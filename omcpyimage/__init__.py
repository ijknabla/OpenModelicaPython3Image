import json
import logging
import os
import re
from asyncio import create_subprocess_exec, gather, run, sleep
from collections import defaultdict
from collections.abc import Callable, Coroutine, Iterable
from contextlib import AsyncExitStack
from functools import reduce, wraps
from itertools import product
from operator import or_
from pathlib import Path
from subprocess import PIPE
from typing import Any, ParamSpec, TypeVar

from aiohttp import ClientSession
from lxml.html import fromstring

from ._apis import parse_omc_version
from ._types import Debian, OMCVersion, Verbosity, Version

logger = logging.getLogger(__name__)

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
        category = defaultdict[Version, set[OMCVersion]](set)

        Verbosity.SLIGHTLY_VERBOSE.log(logger, f"({debian}) Download {uri}")
        async with AsyncExitStack() as stack:
            session = await stack.enter_async_context(ClientSession())
            response = await stack.enter_async_context(session.get(uri))
            root = fromstring(await response.read())
            Verbosity.VERBOSE.log(
                logger, f"({debian}) Download {uri} completed!"
            )
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
                    Verbosity.VERBOSE.log(
                        logger,
                        (
                            f"({debian}) Extract omc{str(omc_version):<18} "
                            f"from {match.group(0)}"
                        ),
                    )
                except ValueError:
                    continue
                category[omc_version.short].add(omc_version)

        Verbosity.SLIGHTLY_VERBOSE.log(
            logger,
            (
                f"({debian}) Extract #{sum(map(len, category.values()))} "
                f"omc versions from {uri}"
            ),
        )
        return {
            (debian, version): max(omc_versions, key=lambda v: (v.release, v))
            for version, omc_versions in sorted(category.items())
        }

    return reduce(or_, await gather(*map(get_openmodelica_versions, debians)))


async def get_python_vs_debian(
    py_short_versions: Iterable[Version], debian: Iterable[Debian]
) -> set[tuple[Version, Debian]]:
    keys = tuple(product(py_short_versions, debian))
    return set(
        key
        for key, exists in zip(
            keys,
            await gather(
                *(
                    _exists_in_dockerhub(version, debian)
                    for version, debian in keys
                )
            ),
        )
        if exists
    )


async def _exists_in_dockerhub(
    python: Version,
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
    elif re.match(rb"^toomanyrequests:", err):
        print(err)
        await sleep(2 * 60)
        return await _exists_in_dockerhub(python, debian)
    else:
        raise RuntimeError(f"{retcode=!r}", f"{err=!r}")


async def download(uri: str, dst: Path) -> None:
    if dst.exists():
        return
    os.makedirs(dst.parent, exist_ok=True)
    async with AsyncExitStack() as stack:
        session = await stack.enter_async_context(ClientSession())
        response = await stack.enter_async_context(session.get(uri))
        dst.write_bytes(await response.read())
