from asyncio import gather
from typing import IO

import click
import toml

from . import get_openmodelica_vs_debian, get_python_vs_debian, run_coroutine
from ._apis import is_config, iter_debian
from ._types import Debian, OMCPackage, Python


@click.command
@click.argument("config_io", metavar="CONFIG.TOML", type=click.File("r"))
@run_coroutine
async def main(
    config_io: IO[str],
) -> None:
    config = toml.load(config_io)
    assert is_config(config)

    openmodelica_vs_debian = await get_openmodelica_vs_debian(
        iter_debian(config)
    )

    for (debian, _), omc_version in openmodelica_vs_debian.items():
        for omc_package in OMCPackage:
            print(f"{omc_package.get_uri(debian, omc_version)}")

    return
    openmodelica_vs_debian, python_vs_debian = await gather(
        get_openmodelica_vs_debian([Debian("bullseye")]),
        get_python_vs_debian(),
    )

    for python, row in zip(Python, python_vs_debian):
        for debian, value in zip(Debian, row):
            print(f"{python}-{debian}", value)


if __name__ == "__main__":
    main()
