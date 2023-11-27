from asyncio import Lock, Semaphore, TimeoutError, gather, wait_for
from collections import defaultdict
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from functools import partial
from typing import IO

import click
import toml

from . import ImageBuilder, builder, run_coroutine
from .config import Config
from .types import LongVersion


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

    build_images = {
        image: await builder.get_ubuntu_image(image) for image in config.from_
    }
    python_versions = [
        max([lv async for lv in builder.search_python_version(sv)])
        for sv in config.python
    ]

    locks = defaultdict[str | LongVersion, Lock](Lock)

    tags = await gather(
        *(
            builder.build(
                build_image,
                openmodelica_image,
                version,
                partial(lock_all, locks[build_image], locks[version]),
            )
            for openmodelica_image, build_image in build_images.items()
            for version in python_versions
        )
    )
    for tag in sorted(tags):
        print(tag)

    return

    if limit is not None:
        lock = Semaphore(limit)
    else:
        lock = None
    await ImageBuilder(config).build(lock)


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
