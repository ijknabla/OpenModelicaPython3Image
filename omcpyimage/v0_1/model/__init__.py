from __future__ import annotations

from asyncio import TaskGroup, get_running_loop, run
from collections.abc import Callable, Iterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack, contextmanager
from functools import wraps
from multiprocessing import Manager, Pipe
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event
from typing import Self

from PySide6.QtCore import QObject, QRunnable, QThreadPool

from ..annotation import Signal


class Model(QObject):
    @classmethod
    @contextmanager
    def open(
        cls, parent: QObject, *, executor: ProcessPoolExecutor, pool: QThreadPool
    ) -> Iterator[Self]:
        with ExitStack() as stack:
            client_connection, server_connection = Pipe()
            stack.callback(server_connection.close)

            self = cls(parent)
            self.request.connect(client_connection.send)
            pool.start(Client(client_connection, self.on_response))

            manager = stack.enter_context(Manager())
            stop = manager.Event()
            stack.callback(stop.set)
            future = executor.submit(serve, stop, server_connection)

            yield self

        if exception := future.exception():
            raise exception

    request = Signal(object)

    def on_response(self, response: object) -> None:
        raise NotImplementedError(response)


class Client(QRunnable):
    def __init__(self, connection: Connection, callback: Callable[[object], None]):
        super().__init__()

        self.connection = connection
        self.callback = callback

    def run(self) -> None:
        while True:
            if self.connection.poll():
                try:
                    response = self.connection.recv()
                except EOFError:
                    return
                self.callback(response)


@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def serve(stop: Event, connection: Connection) -> None:
    loop = get_running_loop()

    async with TaskGroup() as group:

        async def reply() -> None:
            request = connection.recv()
            async for response in request.reply():
                connection.send(response)

        loop.add_reader(connection.fileno(), lambda: group.create_task(reply()))

        await loop.run_in_executor(None, stop.wait)
