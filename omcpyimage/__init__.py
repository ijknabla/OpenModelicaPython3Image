import json
import re
from asyncio import (
    FIRST_COMPLETED,
    Queue,
    Task,
    create_subprocess_exec,
    create_task,
    gather,
    run,
    wait,
)
from collections import defaultdict
from collections.abc import AsyncIterator, Callable, Coroutine
from contextlib import AsyncExitStack
from dataclasses import dataclass
from functools import partial, wraps
from itertools import product
from subprocess import PIPE
from typing import Any, NamedTuple, ParamSpec, TypeVar

from aiohttp import ClientSession
from lxml.html import HtmlElement, fromstring
from numpy import array, bool_, int8
from numpy.typing import NDArray

from ._api import is_debian, is_long_version
from ._types import Config, Debian, LongVersion, OpenModelica, Python, Version

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class ImageBuilder:
    config: Config

    @property
    def omc_versions(self) -> list[Version]:
        return list(map(Version.parse, self.config["omc"]))

    @property
    def py_versions(self) -> list[Version]:
        return list(map(Version.parse, self.config["py"]))

    @property
    def debians(self) -> list[Debian]:
        return [Debian[debian] for debian in self.config["debian"]]

    async def iter_available_omc_versions(
        self,
    ) -> AsyncIterator[tuple[LongVersion, Debian]]:
        releases_uri = (
            "https://build.openmodelica.org/omc/builds/linux/releases/"
        )
        omc_versions = set(self.omc_versions)

        queue = Queue[tuple[LongVersion, Debian]]()

        async def put(v: LongVersion, d: Debian) -> None:
            await queue.put((v, d))

        tasks = list[Task[None]]()
        async with ClientSession() as session:
            releases = await download_tree(session, uri=f"{releases_uri}")
            for href in releases.xpath("//a/@href"):
                if not (is_long_version(href[:-1]) and href[-1] == "/"):
                    continue
                long_version = LongVersion.parse(href[:-1])
                if long_version.as_short not in omc_versions:
                    continue
                tasks.append(
                    create_task(
                        self.put_available_omc_versions(
                            partial(put, long_version),
                            uri=f"{releases_uri}{href}dists/",
                        )
                    )
                )

        async def stop_iteration() -> None:
            await gather(*tasks)
            await queue.join()

        while True:
            get = create_task(queue.get())
            done, _ = await wait(
                [get, create_task(stop_iteration())],
                return_when=FIRST_COMPLETED,
            )
            if get in done:
                try:
                    yield get.result()
                finally:
                    queue.task_done()
            else:
                return

    async def put_available_omc_versions(
        self,
        put: Callable[[Debian], Coroutine[Any, Any, None]],
        uri: str,
    ) -> None:
        debians = set(self.debians)
        async with ClientSession() as session:
            dists = await download_tree(session, uri=f"{uri}")
            for href in dists.xpath("//a/@href"):
                if not (is_debian(href[:-1]) and href[-1] == "/"):
                    continue
                debian = Debian[href[:-1]]
                if debian not in debians:
                    continue
                await put(debian)

    async def build(self) -> None:
        async for (
            omc_long_version,
            debian,
        ) in self.iter_available_omc_versions():
            print(omc_long_version, debian)


async def download_tree(session: ClientSession, uri: str) -> HtmlElement:
    async with session.get(uri) as response:
        return fromstring(await response.read())


ARCHITECTURE = "amd64"


def run_coroutine(
    afunc: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, T]:
    @wraps(afunc)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return run(afunc(*args, **kwargs))

    return wrapped


async def get_openmodelica_vs_debian() -> NDArray[int8]:
    category = defaultdict[tuple[int, int, Debian], set[tuple[int, int]]](
        lambda: {(-1, -1)}
    )
    semvers: list[SemanticVersion]
    for debian, semvers in zip(
        Debian,
        await gather(*map(_get_openmodelica_versions, Debian)),
    ):
        for semver in semvers:
            category[(*semver.major_minor, debian)].add(semver.patch_build)

    flat = array(
        [
            max(category[*openmodelica.tuple, debian])
            for openmodelica, debian in product(OpenModelica, Debian)
        ],
        dtype=int8,
    )
    return flat.reshape([len(OpenModelica), len(Debian), 2])


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
