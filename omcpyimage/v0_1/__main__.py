from __future__ import annotations

from asyncio import gather, run
from collections import defaultdict
from functools import wraps
from itertools import product
from sys import exit
from typing import TYPE_CHECKING

import click
from pydantic import BaseModel
from PySide6.QtWidgets import QApplication

from . import Image, Version
from .widget.mainwindow import MainWindow

if TYPE_CHECKING:
    from collections.abc import Sequence

    from . import OMVersion, PyVersion


@click.group()
def main() -> None: ...


class Request(BaseModel):
    payload: str

    async def reply(self):
        yield Response(payload=self.payload)


class Response(BaseModel):
    payload: str


@main.command()
def gui() -> None:
    app = QApplication()

    with MainWindow.open() as main_window:
        main_window.show()

        main_window.model.request.emit(Request(payload="hoge"))

        status = app.exec()

    exit(status)


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

    await gather(*(im.deploy(tags[im], push=push) for im in image))

    print("=" * 72)
    for _, tt in sorted(tags.items()):
        for t in tt:
            print(f"- {t}")
    print("=" * 72)


if __name__ == "__main__":
    main()
