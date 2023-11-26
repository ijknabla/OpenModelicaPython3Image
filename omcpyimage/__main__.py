from asyncio import Semaphore, gather
from typing import IO

import click
import toml

from . import ImageBuilder, builder, run_coroutine
from .config import Config


@click.command
@click.argument(
    "config_io",
    metavar="CONFIG.TOML",
    type=click.File(mode="r", encoding="utf-8"),
)
@click.option("--limit", type=int, default=1)
@run_coroutine
async def main(config_io: IO[str], limit: int) -> None:
    config = Config.model_validate(toml.load(config_io))
    lock = Semaphore(max(limit, 1))

    await gather(*(builder.pull(image) for image in config.from_))

    return

    if limit is not None:
        lock = Semaphore(limit)
    else:
        lock = None
    await ImageBuilder(config).build(lock)


if __name__ == "__main__":
    main()
