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
from collections.abc import (
    AsyncIterator,
    Callable,
    Coroutine,
    Iterable,
    Iterator,
)
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import partial, wraps
from itertools import product
from pathlib import Path
from subprocess import PIPE
from tempfile import TemporaryDirectory
from typing import Any, ParamSpec, TypeVar

from aiohttp import ClientSession
from lxml.html import HtmlElement, fromstring
from pkg_resources import resource_string

from ._api import is_debian, is_long_version
from ._types import Config, Debian, LongVersion, Version

P = ParamSpec("P")
T = TypeVar("T")


async def download_tree(session: ClientSession, uri: str) -> HtmlElement:
    async with session.get(uri) as response:
        return fromstring(await response.read())


def run_coroutine(
    afunc: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, T]:
    @wraps(afunc)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return run(afunc(*args, **kwargs))

    return wrapped


@dataclass
class ImageBuilder:
    config: Config
    manifest_expiration: timedelta = field(default=timedelta(days=2))
    image_name = "ijknabla/openmodelica-python3"

    @property
    def omc_versions(self) -> list[Version]:
        return list(map(Version.parse, self.config["omc"]))

    @property
    def py_versions(self) -> list[Version]:
        return list(map(Version.parse, self.config["py"]))

    @property
    def debians(self) -> list[Debian]:
        return [Debian[debian] for debian in self.config["debian"]]

    async def build(self) -> None:
        omc_long_versions, py_versions = await gather(
            self.get_omc_long_versions(), self.get_py_versions()
        )

        def iter_targets() -> Iterator[tuple[LongVersion, Version, Debian]]:
            for omc_version, py_version, debian in product(
                self.omc_versions, self.py_versions, self.debians
            ):
                omc_long_version = omc_long_versions.get((omc_version, debian))
                if omc_long_version is None:
                    continue
                if (py_version, debian) not in py_versions:
                    continue

                assert omc_long_version.as_short == omc_version
                yield omc_long_version, py_version, debian

        tags = await gather(
            *(self.docker_build_and_push(*target) for target in iter_targets())
        )
        for tag in tags:
            print("=>", tag)

    async def docker_build_and_push(
        self, omc_version: LongVersion, py_version: Version, debian: Debian
    ) -> str:
        tag = (
            f"{self.image_name}"
            f":omc{omc_version.as_short}-py{py_version}-{debian}"
        )

        with ExitStack() as stack:
            directory = Path(stack.enter_context(TemporaryDirectory()))
            (directory / "Dockerfile").write_bytes(
                resource_string(__name__, "Dockerfile")
            )

            docker_build = [
                "docker",
                "build",
                f"{directory}",
                f"--tag={tag}",
                f"--build-arg=OMC_VERSION={omc_version}",
                f"--build-arg=PY_VERSION={py_version}",
                f"--build-arg=DEBIAN_CODENAME={debian}",
            ]
            print(f"run {' '.join(docker_build)}")

            process = await create_subprocess_exec(
                *docker_build,
                stdout=PIPE,
                stderr=PIPE,
            )

            _, err = await process.communicate()
            retcode = process.returncode
            if process.returncode != 0:
                raise RuntimeError(f"{retcode=!r}", f"{err=!r}")

            print(f"finish {' '.join(docker_build)}")

        docker_push = [
            "docker",
            "push",
            f"{tag}",
        ]
        print(f"run {' '.join(docker_push)}")

        process = await create_subprocess_exec(
            *docker_push,
            stdout=PIPE,
            stderr=PIPE,
        )

        _, err = await process.communicate()
        retcode = process.returncode
        if process.returncode != 0:
            raise RuntimeError(f"{retcode=!r}", f"{err=!r}")

        print(f"finish {' '.join(docker_push)}")

        return tag

    async def get_omc_long_versions(
        self,
    ) -> dict[tuple[Version, Debian], LongVersion]:
        category = defaultdict[tuple[Version, Debian], set[LongVersion]](set)
        async for (
            long_version,
            debian,
        ) in self.iter_available_omc_versions():
            version = long_version.as_short
            category[(version, debian)].add(long_version)

        return {
            (version, debian): max(long_versions)
            for (version, debian), long_versions in sorted(category.items())
        }

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

        put_tasks = list[Task[None]]()
        async with ClientSession() as session:
            releases = await download_tree(session, uri=f"{releases_uri}")
            for href in releases.xpath("//a/@href"):
                if not (is_long_version(href[:-1]) and href[-1] == "/"):
                    continue
                long_version = LongVersion.parse(href[:-1])
                if long_version.as_short not in omc_versions:
                    continue
                put_tasks.append(
                    create_task(
                        self.put_available_omc_versions(
                            partial(put, long_version),
                            uri=f"{releases_uri}{href}dists/",
                        )
                    )
                )

        async for i in self.iter_from_queue(queue, put_tasks):
            yield i

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

    async def get_py_versions(self) -> list[tuple[Version, Debian]]:
        py_version_exists = await gather(
            *(
                self.py_version_exists(version, debian)
                for version, debian in product(self.py_versions, self.debians)
            )
        )

        return sorted(
            (version, debian)
            for version, debian, exists in py_version_exists
            if exists
        )

    async def py_version_exists(
        self, version: Version, debian: Debian
    ) -> tuple[Version, Debian, bool]:
        py_image_cache = self.config["cache"]["py-images"]
        py_image = f"python:{version}-{debian}"
        now = datetime.utcnow()

        def update_needed() -> bool:
            cache = py_image_cache.get(py_image)
            if cache is None:
                return True
            return (now - cache["updated-at"]) > self.manifest_expiration

        if update_needed():
            docker_manifest_inspect = [
                "docker",
                "manifest",
                "inspect",
                py_image,
            ]
            print(f"run {' '.join(docker_manifest_inspect)}")
            process = await create_subprocess_exec(
                *docker_manifest_inspect,
                stdout=PIPE,
                stderr=PIPE,
            )
            _, err = await process.communicate()
            retcode = process.returncode

            if process.returncode == 0:
                exists = True
            elif re.match(rb"^no\s*such\s*manifest\s*:", err):
                exists = False
            else:
                raise RuntimeError(f"{retcode=!r}", f"{err=!r}")

            py_image_cache[py_image] = {"updated-at": now, "exists": exists}

        cache = py_image_cache[py_image]

        return version, debian, cache["exists"]

    @staticmethod
    async def iter_from_queue(
        queue: Queue[T], put_tasks: Iterable[Task[None]]
    ) -> AsyncIterator[T]:
        async def stop_iteration() -> None:
            await gather(*put_tasks)
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
