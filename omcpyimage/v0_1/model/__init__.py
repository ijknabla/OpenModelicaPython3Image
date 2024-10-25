from __future__ import annotations

__all__ = ("Application", "findversion", "open_model")

import logging
from asyncio import (
    FIRST_COMPLETED,
    Future,
    Task,
    create_task,
    get_running_loop,
    run,
    wait,
)
from collections.abc import AsyncIterator, Iterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack, contextmanager
from functools import wraps
from multiprocessing import Manager, Pipe
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event
from typing import Any, Protocol

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Slot

from ..annotation import Signal, SignalInstance
from . import findversion
from .constant import Application

logger = logging.getLogger(__name__)


@contextmanager
def open_model(
    parent: QObject | None = None,
    executor: ProcessPoolExecutor | None = None,
    threadpool: QThreadPool | None = None,
) -> Iterator[Model]:
    with ExitStack() as stack:
        if executor is None:
            executor = stack.enter_context(ProcessPoolExecutor())
        if threadpool is None:
            threadpool = QThreadPool()

        connection1, connection2 = Pipe()
        stack.callback(connection1.close)
        stack.callback(connection2.close)

        manager = stack.enter_context(Manager())
        terminate = manager.Event()
        stack.callback(terminate.set)

        executor.submit(serve, terminate=terminate, connection=connection1)

        model = Model(parent)

        agent = ConnectionAgent(model, connection=connection2, threadpool=threadpool)
        model.setAgent(agent)

        yield model


class SupportsRequest(Protocol):
    def reply(self) -> AsyncIterator[Any]: ...


class ConnectionAgent(QObject):
    send = Signal(SupportsRequest)  # type: ignore [type-abstract]
    recv = Signal(object)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        connection: Connection,
        threadpool: QThreadPool,
    ) -> None:
        super().__init__(parent)

        self.send.connect(connection.send)
        threadpool.start(ConnectionAgent._Listener(connection, self.recv))

    class _Listener(QRunnable):
        def __init__(
            self,
            connection: Connection,
            signal: SignalInstance[object],
        ) -> None:
            super().__init__()

            self.connection = connection
            self.signal = signal

        @Slot()
        def run(self) -> None:
            while not self.connection.closed:
                if not self.connection.poll():
                    continue
                self.signal.emit(self.connection.recv())


class Model(QObject):
    findversion_request = Signal(findversion.Request)
    findversion_response = Signal(findversion.Response)

    def setAgent(self, agent: ConnectionAgent) -> None:
        agent.recv.connect(self._on_recv)

        self.findversion_request.connect(agent.send.emit)

    def _on_recv(self, response: Any) -> None:
        if isinstance(response, findversion.Response):
            self.findversion_response.emit(response)
        else:
            raise NotImplementedError(response)


@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def serve(*, terminate: Event, connection: Connection) -> None:
    loop = get_running_loop()

    wait_terminate = loop.run_in_executor(None, terminate.wait)
    pending = set[Future[bool] | Task[None]]({wait_terminate})

    async def reply_and_send(request: SupportsRequest) -> None:
        async for response in request.reply():
            connection.send(response)

    def reader() -> None:
        while connection.poll():
            request = connection.recv()
            pending.add(create_task(reply_and_send(request)))

    loop.add_reader(connection.fileno(), reader)

    while pending:
        done, pending = await wait(pending, return_when=FIRST_COMPLETED)

        for task in done:
            print(task)

        if wait_terminate in done:
            for task in pending:
                task.cancel()
