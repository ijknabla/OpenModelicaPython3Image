from asyncio import gather
from itertools import product
from pathlib import Path

import click
import toml

from . import get_openmodelica_vs_debian, get_python_vs_debian, run_coroutine
from ._api import is_config
from ._types import Debian, OpenModelica, Python


@click.command
@click.argument(
    "config_path",
    metavar="CONFIG.TOML",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, path_type=Path
    ),
)
@run_coroutine
async def main(
    config_path: Path,
) -> None:
    config = toml.loads(config_path.read_text(encoding="utf-8"))
    assert is_config(config)

    try:
        ...
    finally:
        assert is_config(config)
        config_path.write_text(toml.dumps(config), encoding="utf-8")

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
