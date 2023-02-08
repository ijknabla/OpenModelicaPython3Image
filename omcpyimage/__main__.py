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
@run_coroutine
async def main(
    config_path: Path,
) -> None:
    config = toml.loads(config_path.read_text(encoding="utf-8"))
    assert is_config(config)

    try:
        await ImageBuilder(config).build()
    finally:
        assert is_config(config)
        sort_cache(config)
        config_path.write_text(toml.dumps(config), encoding="utf-8")


if __name__ == "__main__":
    main()
