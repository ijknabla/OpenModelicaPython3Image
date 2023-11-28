from __future__ import annotations

import asyncio
from asyncio import Lock, TimeoutError, gather, wait_for
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import AsyncExitStack, asynccontextmanager
from functools import wraps
from operator import itemgetter
from typing import IO, Any, ParamSpec, TypeVar

import click
import toml

from . import builder
from .builder import OpenmodelicaPythonImage
from .config import Config

P = ParamSpec("P")
T = TypeVar("T")


def execute_coroutine(
    f: Callable[P, Coroutine[Any, Any, T]]
) -> Callable[P, T]:
    @wraps(f)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(f(*args, **kwargs))

    return wrapped


@click.command
@click.argument(
    "config_io",
    metavar="CONFIG.TOML",
    type=click.File(mode="r", encoding="utf-8"),
)
@click.option("--limit", type=int, default=1)
@execute_coroutine
async def main(config_io: IO[str], limit: int) -> None:
    config = Config.model_validate(toml.load(config_io))

    pythons = await builder.search_python_versions(config.python)

    ubuntu_openmodelica = await builder.categorize_by_ubuntu_release(
        config.from_
    )

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
        if image.openmodelica
        in map(itemgetter(0), ubuntu_openmodelica.values())
    }

    group0 = images & ubuntu0 & python0
    group1 = images & ubuntu0 - python0
    group2 = images - ubuntu0

    assert (group0 | group1 | group2) == images

    tags = list[str]()
    for group in [group0, group1, group2]:
        tags += await gather(
            *(
                builder.build(image.ubuntu, image.openmodelica, image.python)
                for image in sorted(group)
            )
        )
    await gather(*(builder.push(tag) for tag in tags))
    for tag in sorted(tags):
        print(tag)


@asynccontextmanager
async def lock_all(*locks: Lock) -> AsyncGenerator[None, None]:
    async with AsyncExitStack() as stack:
        while True:
            lock_all = gather(
                *(stack.enter_async_context(lock) for lock in locks)
            )

            try:
                await wait_for(lock_all, 1e-3)
                break
            except TimeoutError:
                await stack.aclose()
                continue

        yield


if __name__ == "__main__":
    main()
