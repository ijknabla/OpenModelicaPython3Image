from asyncio import gather
from typing import IO

import click
import toml

from . import get_openmodelica_vs_debian, get_python_vs_debian, run_coroutine
from ._apis import is_config
from ._types import Debian, DebianName, Python


@click.command
@click.argument("config_io", metavar="CONFIG.TOML", type=click.File("r"))
@run_coroutine
async def main(
    config_io: IO[str],
) -> None:
    config = toml.load(config_io)
    assert is_config(config)

    openmodelica_vs_debian = await get_openmodelica_vs_debian(config["debian"])

    for (distro_name, _), omc_version in openmodelica_vs_debian.items():
        print(f"{distro_name=!s}, {omc_version=!s}")

    return
    openmodelica_vs_debian, python_vs_debian = await gather(
        get_openmodelica_vs_debian([DebianName("bullseye")]),
        get_python_vs_debian(),
    )

    for python, row in zip(Python, python_vs_debian):
        for debian, value in zip(Debian, row):
            print(f"{python}-{debian}", value)


if __name__ == "__main__":
    main()
