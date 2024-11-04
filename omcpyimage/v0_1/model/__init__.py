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
            # stack.callback(print, "server_connection.close")
            # stack.callback(server_connection.close)

            self = cls(parent)
            self.request.connect(client_connection.send)
            pool.start(Client(client_connection, self.on_response))

            stack.callback(print, "manager.__exit__")
            manager = stack.enter_context(Manager())
            stop = manager.Event()
            # stack.callback(stop.set)
            future = executor.submit(serve, stop, server_connection)

            yield self

            stop.set()
            print(future.exception())
            client_connection.close()
            # server_connection.close()


    request = Signal(object)

    def on_response(self, response: object) -> None:
        print(response)
        return
        raise NotImplementedError(f"{response=!r}")


class Client(QRunnable):
    def __init__(self, connection: Connection, callback: Callable[[object], None]):
        super().__init__()

        self.connection = connection
        self.callback = callback

    def run(self) -> None:
        while not self.connection.closed:
            try:
                if not self.connection.poll():
                    continue
                response = self.connection.recv()
            except EOFError:
                return
            except Exception as e:
                print(e)
                continue

            self.callback(response)


@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def serve(stop: Event, connection: Connection) -> None:
    loop = get_running_loop()

    async with TaskGroup() as group:

        def callback():
            print(":-)")
            try:
                group.create_task(reply())
            except Exception as e:
                print(e)
                raise

        async def reply() -> None:
            try:
                request = await loop.run_in_executor(connection.recv)
                print(request)
                async for response in request.reply():
                    connection.send(response)
            except Exception as e:
                print(e)
                raise

        loop.add_reader(connection.fileno(), callback)

        pending = {loop.run_in_executor(None, stop.wait)}
        while not stop.wait(1e-3) and not connection.closed:
            continue
            print(f"{stop.wait(1e-3)=!r}")
            # from asyncio import wait
            # _, pending = await wait(pending, timeout=1e-3)

            # while not (await loop.run_in_executor(None, stop.wait, 1e-3)):
            # print(".", end="", flush=True)

        print("OK!!")
