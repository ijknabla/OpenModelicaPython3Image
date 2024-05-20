from __future__ import annotations

from asyncio.subprocess import Process
from collections.abc import AsyncGenerator, Iterator
from contextlib import asynccontextmanager, contextmanager, suppress
from subprocess import Popen
from typing import AnyStr


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
