import json
import os
import re
from asyncio import create_subprocess_exec, gather, run
from collections import defaultdict
from collections.abc import Callable, Coroutine, Iterable
from contextlib import AsyncExitStack
from functools import reduce, wraps
from itertools import product
from operator import or_
from pathlib import Path
from subprocess import PIPE
from typing import Any, ParamSpec, TypeVar
from urllib.parse import urlparse

from aiohttp import ClientSession
from lxml.html import fromstring
from numpy import array, bool_
from numpy.typing import NDArray

from ._apis import parse_omc_version
from ._types import Debian, OMCPackage, OMCVersion, Python, Version

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


async def get_openmodelica_vs_debian(
    debians: Iterable[Debian],
) -> dict[tuple[Debian, Version], OMCVersion]:
    DEB_PATTERN = re.compile(
        rf"openmodelica_(?P<version>.*?)_{re.escape(ARCHITECTURE)}\.deb"
    )

    async def get_openmodelica_versions(
        debian: Debian,
    ) -> dict[tuple[Debian, Version], OMCVersion]:
        uri = f"https://build.openmodelica.org/apt/pool/contrib-{debian}/"
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
                (debian, version): max(
                    omc_versions, key=lambda v: (v.release, v)
                )
                for version, omc_versions in sorted(category.items())
            }
        finally:
            print(f"End {uri}")

    return reduce(or_, await gather(*map(get_openmodelica_versions, debians)))


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


async def download_omc_package(
    omc_package: OMCPackage, debian: Debian, version: OMCVersion, path: Path
) -> None:
    uri = omc_package.get_uri(debian, version)
    dst = path / f"{debian}" / Path(urlparse(uri).path).name
    if dst.exists():
        return
    os.makedirs(dst.parent, exist_ok=True)
    async with AsyncExitStack() as stack:
        session = await stack.enter_async_context(ClientSession())
        response = await stack.enter_async_context(session.get(uri))
        dst.write_bytes(await response.read())
