from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

__version__ = "0.0.1a0.dev0"

P = ParamSpec("P")
T = TypeVar("T")


def run_coroutine(
    afunc: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, T]:
    @wraps(afunc)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(afunc(*args, **kwargs))

    return wrapped


class NoLock:
    async def __aenter__(self) -> None:
        return

    async def __aexit__(self, *exc_info: Any) -> None:
        return
