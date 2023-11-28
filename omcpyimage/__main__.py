from __future__ import annotations

import asyncio
from asyncio import Lock, TimeoutError, gather, wait_for
from collections.abc import AsyncGenerator, Callable, Coroutine
from contextlib import AsyncExitStack, asynccontextmanager
from functools import wraps
from itertools import islice
from typing import IO, Any, ParamSpec, TypeVar

import click
import toml

from . import builder
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

    python_versions = await builder.search_python_versions(config.python)

    categoeized_by_ubuntu = await builder.categorize_by_ubuntu_release(
        config.from_
    )

    first = [
        (ubuntu_image, openmodelica_image, python_version)
        for ubuntu_image, categorized in categoeized_by_ubuntu.items()
        for openmodelica_image in islice(categorized, 1)
        for python_version in islice(python_versions, 1)
    ]
    second = [
        (ubuntu_image, openmodelica_image, python_version)
        for ubuntu_image, categorized in categoeized_by_ubuntu.items()
        for openmodelica_image in islice(categorized, 1)
        for python_version in islice(python_versions, 1, None)
    ]
    third = [
        (ubuntu_image, openmodelica_image, python_version)
        for ubuntu_image, categorized in categoeized_by_ubuntu.items()
        for openmodelica_image in islice(categorized, 1, None)
        for python_version in python_versions
    ]

    # locks = defaultdict[str | LongVersion, Lock](Lock)

    tags = list[str]()
    for group in [first, second, third]:
        tags += await gather(
            *(
                builder.build(
                    ubuntu_image,
                    openmodelica_image,
                    python_version,
                    # partial(lock_all, locks[ubuntu_image], locks[python_version]),  # noqa: E501
                )
                for ubuntu_image, openmodelica_image, python_version in group
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
