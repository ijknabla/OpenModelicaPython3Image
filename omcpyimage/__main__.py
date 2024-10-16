from __future__ import annotations

import asyncio
from asyncio import Lock, TimeoutError, gather, wait_for
from collections.abc import AsyncGenerator, Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from contextlib import AsyncExitStack, asynccontextmanager
from functools import wraps
from operator import itemgetter
from typing import IO, Any, ParamSpec, TypeVar, TypeVarTuple

import click
import tomllib
from PySide6.QtWidgets import QApplication

from .builder import (
    OpenmodelicaPythonImage,
    categorize_by_ubuntu_release,
    search_python_versions,
)
from .config import Config
from .model.builder import Builder
from .widget.mainwindow import MainWindow

P = ParamSpec("P")
T = TypeVar("T")
Ts = TypeVarTuple("Ts")


def execute_coroutine(f: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, T]:
    @wraps(f)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(f(*args, **kwargs))

    return wrapped


@click.command
@click.argument(
    "config_io",
    metavar="CONFIG.TOML",
    type=click.File(mode="rb"),
)
@click.option("--limit", type=int, default=1)
@execute_coroutine
async def main(config_io: IO[bytes], limit: int) -> None:
    config = Config.model_validate(tomllib.load(config_io))

    pythons = await search_python_versions(config.python)

    ubuntu_openmodelica = await categorize_by_ubuntu_release(config.from_)

    images = {
        OpenmodelicaPythonImage(
            base="ijknabla/openmodelica",
            ubuntu=ubuntu,
            openmodelica=openmodelica,
            python=python,
        )
        for ubuntu, openmodelicas in ubuntu_openmodelica.items()
        for openmodelica in openmodelicas
        for python in pythons
    }

    python0 = {image for image in images if image.python == pythons[0]}
    ubuntu0 = {
        image
        for image in images
        if image.openmodelica in map(itemgetter(0), ubuntu_openmodelica.values())
    }

    group0 = images & ubuntu0 & python0
    group1 = images & ubuntu0 - python0
    group2 = images - ubuntu0

    assert (group0 | group1 | group2) == images

    with ThreadPoolExecutor() as executor:
        app = QApplication()

        builder = Builder(
            executor=executor, group0=group0, group1=group1, group2=group2
        )

        mainWindow = MainWindow()
        mainWindow.setImages(images)

        builder.process_start.connect(mainWindow.update_process_status)
        builder.process_returncode.connect(mainWindow.update_process_status)

        mainWindow.show()

        mainWindow.ui.startButton.pressed.connect(builder.start)

        exit(app.exec())

    # await gather(*(image.pull() for image in images), return_exceptions=True)
    # for group in [group0, group1, group2]:
    #     await gather(*(image.build() for image in sorted(group)))
    # await gather(*(image.push() for image in images))
    # for image in sorted(images):
    #     print(image)


@asynccontextmanager
async def lock_all(*locks: Lock) -> AsyncGenerator[None, None]:
    async with AsyncExitStack() as stack:
        while True:
            lock_all = gather(*(stack.enter_async_context(lock) for lock in locks))

            try:
                await wait_for(lock_all, 1e-3)
                break
            except TimeoutError:
                await stack.aclose()
                continue

        yield


if __name__ == "__main__":
    main()
