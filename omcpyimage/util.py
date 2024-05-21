from __future__ import annotations

from asyncio import Future, get_running_loop
from asyncio.subprocess import Process
from collections.abc import AsyncGenerator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager, suppress
from functools import partial, wraps
from subprocess import Popen
from typing import AnyStr, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def in_executor(f: Callable[P, T]) -> Callable[P, Future[T]]:
    @wraps(f)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> Future[T]:
        return get_running_loop().run_in_executor(None, partial(f, *args, **kwargs))

    return wrapped


@contextmanager
def terminating(
    process: Popen[AnyStr],
) -> Iterator[Popen[AnyStr]]:
    try:
        yield process
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()


@asynccontextmanager
async def aterminating(
    process: Process,
) -> AsyncGenerator[Process, None]:
    try:
        yield process
    finally:
        with suppress(ProcessLookupError):
            process.terminate()
            await process.wait()
