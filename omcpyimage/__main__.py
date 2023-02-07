import logging
import shutil
from asyncio import Event, create_subprocess_exec, create_task, gather, sleep
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import dataclass, field
from datetime import datetime
from itertools import product
from pathlib import Path
from subprocess import PIPE
from tempfile import TemporaryDirectory
from typing import IO, Any
from urllib.parse import urlparse

import click
import toml

from . import (
    download,
    get_openmodelica_vs_debian,
    get_python_vs_debian,
    run_coroutine,
)
from ._apis import is_config, iter_debian, iter_omc, iter_py
from ._types import Debian, OMCPackage, Python, Verbosity, Version

logger = logging.getLogger(__name__)


def verbosity_from_count(count: int) -> Verbosity:
    count = min(len(Verbosity), max(0, count))
    for i, verbosity in enumerate(Verbosity):
        if i == count:
            break
    else:
        raise NotImplementedError()

    logging.root.addHandler(logging.StreamHandler())
    logging.root.setLevel(verbosity.value)
    return verbosity


@click.command
@click.argument("config_io", metavar="CONFIG.TOML", type=click.File("r"))
@click.option(
    "--cache",
    "cache_path",
    type=click.Path(file_okay=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--directory",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, path_type=Path
    ),
)
@click.option(
    "-v", "--verbose", "verbosity", count=True, type=verbosity_from_count
)
@run_coroutine
async def main(
    config_io: IO[str],
    cache_path: Path | None,
    directory: Path | None,
    verbosity: Verbosity,
) -> None:
    config = toml.load(config_io)
    assert is_config(config)

    if cache_path is not None and cache_path.exists():
        with cache_path.open("r", encoding="utf-8") as f:
            cache = toml.load(f)
    else:
        cache = {}

    try:
        await Setup(
            omc_short_versions=tuple(iter_omc(config)),
            py_short_versions=tuple(iter_py(config)),
            debians=tuple(iter_debian(config)),
            cache=cache,
        ).run(directory)
    finally:
        if cache_path is not None:
            with cache_path.open("w", encoding="utf-8") as f:
                toml.dump(cache, f)

    return

    debians = list(iter_debian(config))

    openmodelica_vs_debian, python_vs_debian = await gather(
        get_openmodelica_vs_debian(debians),
        get_python_vs_debian(),
    )

    return

    for (debians, _), omc_version in openmodelica_vs_debian.items():
        for omc_package in OMCPackage:
            print(f"{omc_package.get_uri(debians, omc_version)}")

    return
    openmodelica_vs_debian, python_vs_debian = await gather(
        get_openmodelica_vs_debian([Debian("bullseye")]),
        get_python_vs_debian(),
    )

    for python, row in zip(Python, python_vs_debian):
        for debians, value in zip(Debian, row):
            print(f"{python}-{debians}", value)


OMCPackages = dict[tuple[Version, Debian], tuple[Path, ...]]
OMCPackageEvents = defaultdict[tuple[Version, Debian], Event]


@dataclass
class Setup:
    omc_short_versions: tuple[Version, ...]
    py_short_versions: tuple[Version, ...]
    debians: tuple[Debian, ...]
    cache: Any
    __omc_packages: OMCPackages | None = field(default=None, init=False)
    __omc_packages_ready: Event = field(default_factory=Event, init=False)
    __omc_package_events: OMCPackageEvents = field(
        default_factory=lambda: OMCPackageEvents(Event), init=False
    )

    async def run(self, directory: Path | None) -> None:
        with ExitStack() as stack:
            if directory is None:
                directory = Path(stack.enter_context(TemporaryDirectory()))
            await gather(
                self.__download_omc_packages(directory),
                self.__docker_build(directory),
            )

    def __get_destination(
        self, debian: Debian, uri: str, directory: Path
    ) -> Path:
        path_in_uri = Path(urlparse(uri).path)
        return directory / f"{debian}" / path_in_uri.name

    async def __download_omc_packages(self, directory: Path) -> None:
        omc_package_uris = {
            (omc_short_version, debian): tuple(
                omc_package.get_uri(debian, omc_version)
                for omc_package in OMCPackage
            )
            for (debian, omc_short_version), omc_version in (
                await get_openmodelica_vs_debian(self.debians)
            ).items()
            if omc_short_version in self.omc_short_versions
        }
        omc_packages = {
            (omc_short_version, debian): tuple(
                self.__get_destination(debian, uri, directory) for uri in uris
            )
            for (omc_short_version, debian), uris in omc_package_uris.items()
        }

        self.__omc_packages = omc_packages
        self.__omc_packages_ready.set()

        async def _download(key: tuple[Version, Debian]) -> None:
            await gather(
                *(
                    download(uri, dst)
                    for uri, dst in zip(
                        omc_package_uris[key],
                        omc_packages[key],
                    )
                    for uri in omc_package_uris[key]
                )
            )
            version, debian = key
            Verbosity.SLIGHTLY_VERBOSE.log(
                logger, f"All *.deb files for omc{version}-{debian} downloaded"
            )
            self.__omc_package_events[key].set()

        [create_task(_download(key)) for key in omc_package_uris]

    async def __get_omc_packages(self) -> OMCPackages:
        await self.__omc_packages_ready.wait()
        assert self.__omc_packages is not None
        return self.__omc_packages

    async def __get_py_images(self) -> set[tuple[Version, Debian]]:
        result = set[tuple[Version, Debian]]()

        self.cache["py-images"] = self.cache.get("py-images", {})
        py_images_cache = self.cache["py-images"]
        for py, debian in product(self.py_short_versions, self.debians):
            key = f"python:{py}-{debian}"
            if key not in py_images_cache:
                query = (
                    "https://hub.docker.com/_/python/"
                    f"tags?name={py}-{debian} [y/N] "
                )
                exists = None
                while exists is None:
                    await sleep(0.0)
                    match input(query).strip():
                        case "y":
                            exists = True
                        case "N":
                            exists = False
                py_images_cache[key] = dict(
                    updated_at=datetime.utcnow(),
                    exists=exists,
                )

            if py_images_cache[key]["exists"]:
                result.add((py, debian))
        return result

    async def __docker_build(self, directory: Path) -> None:
        omc_packages, py_dockers = await gather(
            self.__get_omc_packages(),
            self.__get_py_images(),
        )

        resolved = sorted(
            (omc, py, debian)
            for omc, py, debian in product(
                self.omc_short_versions,
                self.py_short_versions,
                self.debians,
            )
            if (omc, debian) in omc_packages and (py, debian) in py_dockers
        )

        async def build(omc: Version, py: Version, debian: Debian):
            tag = f"ijknabla/openmodelica:omc{omc}-py{py}-{debian}"

            with ExitStack() as stack:
                temp = Path(stack.enter_context(TemporaryDirectory()))

                await self.__omc_package_events[(omc, debian)].wait()
                omc_packages = sorted(
                    self.__omc_packages[(omc, debian)],
                    key=lambda x: -1 if "omc-common" in x.name else 0,
                )
                omc_package_names = [package.name for package in omc_packages]
                for omc_package, omc_package_name in zip(
                    omc_packages, omc_package_names
                ):
                    dst = temp / omc_package_name
                    if dst.exists():
                        dst.unlink()
                    shutil.copy(omc_package.resolve(), dst)

                self.__get_omc_packages

                dockerfile = temp / "Dockerfile"
                dockerfile.write_text(
                    f"FROM python:{py}-{debian}\n"
                    + "RUN useradd -m user\n"
                    + "".join(
                        f"COPY ./{name} {name}\n" for name in omc_package_names
                    )
                    + "RUN apt update && apt install -y libblas3 liblapack3 libomniorb4-2 libomnithread4 && apt-get clean && rm -rf /var/lib/apt/lists/*\n"
                    # + "RUN apt update && apt install -y "
                    # + " ".join(f"./{name}" for name in omc_package_names)
                    # + " && apt-get clean && rm -rf /var/lib/apt/lists/*\n"
                    # + "RUN rm -rf "
                    # + " ".join(omc_package_names)
                    # + "\n"
                )

                # print(Path(dockerfile).read_text(), end="")
                cmd = [
                    "docker",
                    "build",
                    f"{temp}",
                    f"-t{tag}"
                    # f"--cache-to={directory}",
                    # f"--cache-from={directory}",
                ]
                process = await create_subprocess_exec(
                    *cmd, stdout=PIPE, stderr=PIPE
                )
                _, stderr = await process.communicate()

                print(tag, process.returncode)
                if process.returncode != 0:
                    print(stderr.decode("utf-8"))

        await gather(
            *(
                build(omc=omc, py=py, debian=debian)
                for omc, py, debian in resolved
            )
        )


if __name__ == "__main__":
    main()
