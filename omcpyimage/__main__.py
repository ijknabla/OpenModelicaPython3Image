from asyncio import gather
from typing import IO

import click
import toml

from . import get_openmodelica_vs_distro, get_python_vs_debian, run_coroutine
from ._apis import is_setting
from ._types import Debian, DistroName, Python


@click.command
@click.argument("config_io", metavar="CONFIG.TOML", type=click.File("r"))
@run_coroutine
async def main(
    config_io: IO[str],
) -> None:
    config = toml.load(config_io)
    assert is_setting(config)

    openmodelica_vs_distro = await get_openmodelica_vs_distro(config["distro"])

    for (distro_name, _), omc_version in openmodelica_vs_distro.items():
        print(f"{distro_name=!s}, {omc_version=!s}")

    return
    openmodelica_vs_distro, python_vs_debian = await gather(
        get_openmodelica_vs_distro([DistroName("bullseye")]),
        get_python_vs_debian(),
    )

    for python, row in zip(Python, python_vs_debian):
        for debian, value in zip(Debian, row):
            print(f"{python}-{debian}", value)


if __name__ == "__main__":
    main()
