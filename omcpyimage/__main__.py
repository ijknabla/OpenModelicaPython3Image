from asyncio import gather
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import IO

import click
import toml

from . import (
    download_omc_package,
    get_openmodelica_vs_debian,
    get_python_vs_debian,
    run_coroutine,
)
from ._apis import is_config, iter_debian, iter_omc
from ._types import Debian, OMCPackage, Python


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

    omcs = list(iter_omc(config))
    debians = list(iter_debian(config))

    openmodelica_vs_debian = await get_openmodelica_vs_debian(debians)

    with ExitStack() as stack:
        if directory is None:
            directory = Path(stack.enter_context(TemporaryDirectory()))

        await gather(
            *(
                download_omc_package(
                    omc_package, debian, omc_version, directory
                )
                for (
                    debian,
                    version,
                ), omc_version in openmodelica_vs_debian.items()
                if (version in omcs) and (debian in debians)
                for omc_package in OMCPackage
            )
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


if __name__ == "__main__":
    main()
