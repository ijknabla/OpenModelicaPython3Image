from __future__ import annotations

from asyncio import gather, run
from collections import defaultdict
from functools import wraps
from importlib.resources import read_binary
from itertools import product
from sys import exit
from typing import TYPE_CHECKING

import click
from PySide6.QtWidgets import QApplication

from . import Image, Version
from .widget.mainwindow import MainWindow

if TYPE_CHECKING:
    from collections.abc import Sequence

    from . import OMVersion, PyVersion


@click.group()
def main() -> None: ...


@main.command()
def gui() -> None:
    app = QApplication()

    main_window = MainWindow()
    main_window.show()

    exit(app.exec())


@main.command()
@click.option("--openmodelica", "--om", multiple=True, type=Version.model_validate)
@click.option("--python", "--py", multiple=True, type=Version.model_validate)
@click.option("--push/--no-push", default=False)
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def build(
    openmodelica: Sequence[OMVersion],
    python: Sequence[PyVersion],
    push: bool,
) -> None:
    image = [
        Image(om=om, py=py)
        for om, py in product(
            sorted(set(openmodelica)),
            sorted(set(python)),
        )
    ]
    tags = defaultdict[Image, list[str]](lambda: [])
    for im in image:
        tags[im].append(f"ijknabla/openmodelica:v{im.om!s}-python{im.py!s}")

    categories = defaultdict[tuple[Version, Version], list[Image]](lambda: [])
    for im in image:
        categories[(im.om.short, im.py.short)].append(im)
    for (om, py), ims in categories.items():
        tags[max(ims)].append(f"ijknabla/openmodelica:v{om!s}-python{py!s}")

    dockerfile = read_binary(__package__, "Dockerfile")

    await gather(*(im.deploy(dockerfile, tags[im], push=push) for im in image))

    print("=" * 72)
    for _, tt in sorted(tags.items()):
        for t in tt:
            print(f"- {t}")
    print("=" * 72)


if __name__ == "__main__":
    main()
