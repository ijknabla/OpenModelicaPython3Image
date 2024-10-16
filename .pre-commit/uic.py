from collections.abc import Sequence
from pathlib import Path
from subprocess import run

import click


@click.command()
@click.option(
    "--src",
    type=click.Path(file_okay=False, exists=True, path_type=Path),
    required=True,
)
@click.option(
    "--dst",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
)
@click.argument(
    "ui",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    nargs=-1,
)
def main(src: Path, dst: Path, ui: Sequence[Path]) -> None:
    for _src in ui:
        relpath = _src.relative_to(src)
        _dst = (dst / relpath).with_suffix(".py")
        _dst.parent.mkdir(parents=True, exist_ok=True)
        run(["pyside6-uic", f"{_src}", "-o", f"{_dst}"], check=True)


if __name__ == "__main__":
    main()
