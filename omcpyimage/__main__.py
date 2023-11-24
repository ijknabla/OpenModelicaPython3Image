from asyncio import Semaphore
from pathlib import Path

import click
import toml

from . import ImageBuilder, run_coroutine
from ._api import is_config, sort_cache


@click.command
@click.argument(
    "config_path",
    metavar="CONFIG.TOML",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, path_type=Path
    ),
)
@click.option("--limit", type=int)
@run_coroutine
async def main(config_path: Path, limit: int | None) -> None:
    return
    config = toml.loads(config_path.read_text(encoding="utf-8"))
    assert is_config(config)

    try:
        if limit is not None:
            lock = Semaphore(limit)
        else:
            lock = None
        await ImageBuilder(config).build(lock)
    finally:
        assert is_config(config)
        sort_cache(config)
        config_path.write_text(toml.dumps(config), encoding="utf-8")


if __name__ == "__main__":
    main()
