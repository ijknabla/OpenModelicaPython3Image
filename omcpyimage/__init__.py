import json
import re
from asyncio import create_subprocess_exec, gather, run
from collections import defaultdict
from collections.abc import Callable, Coroutine, Iterable
from contextlib import AsyncExitStack
from functools import reduce, wraps
from itertools import product
from operator import or_
from subprocess import PIPE
from typing import Any, ParamSpec, TypeVar

from aiohttp import ClientSession
from lxml.html import fromstring
from numpy import array, bool_
from numpy.typing import NDArray

from ._apis import parse_omc_version
from ._types import Debian, DistroName, OMCVersion, Python, Version

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


async def get_openmodelica_vs_distro(
    distro_names: Iterable[DistroName],
) -> dict[tuple[DistroName, Version], OMCVersion]:
    DEB_PATTERN = re.compile(
        rf"openmodelica_(?P<version>.*?)_{re.escape(ARCHITECTURE)}\.deb"
    )

    async def get_openmodelica_versions(
        distro_name: DistroName,
    ) -> dict[tuple[DistroName, Version], OMCVersion]:
        uri = f"https://build.openmodelica.org/apt/pool/contrib-{distro_name}/"
        print(f"Begin {uri}")

        category = defaultdict[Version, set[OMCVersion]](set)

        async with AsyncExitStack() as stack:
            session = await stack.enter_async_context(ClientSession())
            response = await stack.enter_async_context(session.get(uri))
            root = fromstring(await response.read())
            for match in map(
                DEB_PATTERN.match,
                root.xpath(
                    "//td/a"
                    '[starts-with(text(), "openmodelica_")]'
                    f'[contains(text(), "_{ARCHITECTURE}.deb")]'
                    "/text()"
                ),
            ):
                assert match is not None
                try:
                    omc_version = parse_omc_version(match.group("version"))
                except ValueError:
                    continue
                category[omc_version.short].add(omc_version)
        try:
            return {
                (distro_name, version): max(
                    omc_versions, key=lambda v: (v.release, v)
                )
                for version, omc_versions in sorted(category.items())
            }
        finally:
            print(f"End {uri}")

    return reduce(
        or_, await gather(*map(get_openmodelica_versions, distro_names))
    )


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
