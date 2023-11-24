from asyncio import Semaphore
from typing import IO

import click
import toml

from . import ImageBuilder, run_coroutine
from ._api import is_config, sort_cache
from .config import Config


@click.command
@click.argument(
    "config_io",
    metavar="CONFIG.TOML",
    type=click.File(mode="r", encoding="utf-8"),
)
@click.option("--limit", type=int)
@run_coroutine
async def main(config_io: IO[str], limit: int | None) -> None:
    config = Config.model_validate(toml.load(config_io))
    return

    try:
        if limit is not None:
            lock = Semaphore(limit)
        else:
            lock = None
        await ImageBuilder(config).build(lock)
    finally:
        assert is_config(config)
        sort_cache(config)


if __name__ == "__main__":
    main()
