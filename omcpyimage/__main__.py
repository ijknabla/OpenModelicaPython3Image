from asyncio import Event, gather
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO
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
from ._types import Debian, OMCPackage, Python, Version


@click.command
@click.argument("config_io", metavar="CONFIG.TOML", type=click.File("r"))
@click.option(
    "--directory",
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, path_type=Path
    ),
)
@run_coroutine
async def main(
    config_io: IO[str],
    directory: Path | None,
) -> None:
    config = toml.load(config_io)
    assert is_config(config)

    await Setup(
        omc_short_versions=tuple(iter_omc(config)),
        py_short_versions=tuple(iter_py(config)),
        debians=tuple(iter_debian(config)),
    ).run(directory)

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
            self.__omc_package_events[key].set()

        await gather(*map(_download, omc_package_uris))

    async def __get_omc_packages(self) -> OMCPackages:
        await self.__omc_packages_ready.wait()
        assert self.__omc_packages is not None
        return self.__omc_packages

    async def __docker_build(self, directory: Path) -> None:
        omc_packages, py_dockers = await gather(
            self.__get_omc_packages(),
            get_python_vs_debian(self.py_short_versions, self.debians),
        )

        resolved = [
            (omc, py, debian)
            for omc, py, debian in product(
                self.omc_short_versions,
                self.py_short_versions,
                self.debians,
            )
            if (omc, debian) in omc_packages and (py, debian) in py_dockers
        ]

        for omc, py, debian in resolved:
            print(f"ijknabla/openmodelica:omc{omc}-py{py}-{debian}")


if __name__ == "__main__":
    main()
