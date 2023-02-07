from asyncio import gather
from itertools import product
from typing import IO

import click
import toml

from . import get_openmodelica_vs_debian, get_python_vs_debian, run_coroutine
from ._api import is_config
from ._types import Debian, OpenModelica, Python


@click.command
@click.argument("config_io", metavar="CONFIG.TOML", type=click.File("r"))
@run_coroutine
async def main(
    config_io: IO[str],
) -> None:
    config = toml.load(config_io)
    assert is_config(config)
    print(config)

    return
    openmodelica_vs_debian, python_vs_debian = await gather(
        get_openmodelica_vs_debian(),
        get_python_vs_debian(),
    )

    for (i, openmodelica), (j, debian) in product(
        enumerate(OpenModelica), enumerate(Debian)
    ):
        patch, build = openmodelica_vs_debian[i, j]
        if 0 <= patch and 0 <= build:
            print(f"{openmodelica}-{debian}", patch, build)

    for python, row in zip(Python, python_vs_debian):
        for debian, value in zip(Debian, row):
            print(f"{python}-{debian}", value)


if __name__ == "__main__":
    main()
