import json
import re
from asyncio import create_subprocess_exec, gather, run
from collections.abc import Callable, Coroutine
from contextlib import AsyncExitStack
from functools import wraps
from itertools import product
from subprocess import PIPE
from typing import Any, NamedTuple, ParamSpec, TypeVar

from aiohttp import ClientSession
from lxml.html import fromstring
from numpy import array, bool_
from numpy.typing import NDArray

from ._types import Debian, Python

P = ParamSpec("P")
T = TypeVar("T")


ARCHITECTURE = "amd64"


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


class SemanticVersion(NamedTuple):
    major: int
    minor: int
    patch: int
    build: int

    @property
    def major_minor(self) -> tuple[int, int]:
        return self.major, self.minor

    @property
    def patch_build(self) -> tuple[int, int]:
        return self.patch, self.build


async def _get_openmodelica_versions(
    debian: Debian,
) -> list[SemanticVersion]:
    result = list[SemanticVersion]()
    uri = f"https://build.openmodelica.org/apt/pool/contrib-{debian}/"
    async with AsyncExitStack() as stack:
        session = await stack.enter_async_context(ClientSession())
        response = await stack.enter_async_context(session.get(uri))
        root = fromstring(await response.read())
        for a in root.xpath("//td/a"):
            match = re.match(
                (
                    r"^openmodelica_(\d+)\.(\d+).(\d+)\-(\d+)"
                    rf"_{ARCHITECTURE}\.deb$"
                ),
                a.text,
            )
            if match is not None:
                result.append(SemanticVersion(*map(int, match.groups())))
    return result


async def _exists_in_dockerhub(
    python: Python,
    debian: Debian,
) -> bool:
    process = await create_subprocess_exec(
        "docker",
        "manifest",
        "inspect",
        f"python:{python}-{debian}",
        stdout=PIPE,
        stderr=PIPE,
    )
    out, err = await process.communicate()
    retcode = process.returncode

    if process.returncode == 0:
        architectures = set(
            manifest["platform"]["architecture"]
            for manifest in json.loads(out)["manifests"]
        )
        assert ARCHITECTURE in architectures
        return True
    elif re.match(rb"^no\s*such\s*manifest\s*:", err):
        return False
    else:
        raise RuntimeError(f"{retcode=!r}", f"{err=!r}")
