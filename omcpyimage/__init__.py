from asyncio import create_subprocess_exec, gather, run
from collections.abc import Callable, Coroutine
from functools import wraps
from itertools import product
from subprocess import DEVNULL
from typing import Any, ParamSpec, TypeVar

from numpy import array, bool_
from numpy.typing import NDArray

from ._types import Debian, Python

P = ParamSpec("P")
T = TypeVar("T")


def run_coroutine(
    afunc: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, T]:
    @wraps(afunc)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return run(afunc(*args, **kwargs))

    return wrapped


async def get_python_vs_debian() -> NDArray[bool_]:
    flat = array(
        await gather(
            *(
                _exists_in_dockerhub(python=p, debian=d)
                for p, d in product(Python, Debian)
            )
        ),
        dtype=bool_,
    )
    return flat.reshape([len(Python), len(Debian)])


async def _exists_in_dockerhub(
    python: Python,
    debian: Debian,
) -> bool:
    process = await create_subprocess_exec(
        "docker",
        "manifest",
        "inspect",
        f"python:{python}-{debian}",
        stdout=DEVNULL,
    )
    await process.communicate()
    return process.returncode == 0
