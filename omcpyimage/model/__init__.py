from __future__ import annotations

from asyncio import run
from collections.abc import Awaitable, Callable
from concurrent.futures import Executor, Future
from functools import partial, wraps
from typing import Concatenate, ParamSpec, Protocol, TypeVar

P = ParamSpec("P")
T = TypeVar("T")
AnySupportsExecutor = TypeVar("AnySupportsExecutor", bound="SupportsExecutor")


def run_in_executor(
    f: Callable[Concatenate[AnySupportsExecutor, P], Awaitable[T]],
) -> Callable[Concatenate[AnySupportsExecutor, P], None]:
    @wraps(f)
    def g(self: AnySupportsExecutor, /, *args: P.args, **kwargs: P.kwargs) -> None:
        future: Future[T] = self.executor.submit(partial(run, f(self, *args, **kwargs)))  # noqa: F841
        # return future.result()

    return g


class SupportsExecutor(Protocol):
    @property
    def executor(self) -> Executor: ...
