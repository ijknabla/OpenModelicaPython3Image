from __future__ import annotations

import re
from asyncio import create_subprocess_exec, gather
from asyncio.subprocess import PIPE
from collections import ChainMap, defaultdict
from collections.abc import AsyncGenerator, Callable, Iterable
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from pathlib import Path

import lxml.html
from aiohttp import ClientSession
from pkg_resources import resource_filename

from .types import LongVersion, ShortVersion
from .util import terminating


async def pull(image: str) -> None:
    process = await create_subprocess_exec("docker", "pull", image)
    async with terminating(process):
        assert await process.wait() == 0


async def build(
    build_image: str,
    openmodelica_image: str,
    python: LongVersion,
    lock: Callable[[], AbstractAsyncContextManager[None]] | None = None,
) -> str:
    openmodelica = LongVersion.parse(openmodelica_image)
    dockerfile = Path(resource_filename(__name__, "Dockerfile")).resolve()

    tag = f"ijknabla/openmodelica:v{openmodelica}-python{python.as_short()}"

    async with AsyncExitStack() as stack:
        pull = await stack.enter_async_context(
            terminating(await create_subprocess_exec("docker", "pull", tag))
        )
        await pull.wait()

        if lock is not None:
            await stack.enter_async_context(lock())
        process = await stack.enter_async_context(
            terminating(
                await create_subprocess_exec(
                    "docker",
                    "build",
                    f"{dockerfile.parent}",
                    f"--tag={tag}",
                    f"--build-arg=BUILD_IMAGE={build_image}",
                    f"--build-arg=OPENMODELICA_IMAGE={openmodelica_image}",
                    f"--build-arg=PYTHON_VERSION={python}",
                )
            )
        )

        assert await process.wait() == 0

    return tag


async def push(image: str) -> None:
    process = await create_subprocess_exec("docker", "push", image)
    async with terminating(process):
        assert await process.wait() == 0


async def search_python_versions(
    shorts: Iterable[ShortVersion],
    source_uri: str = "https://www.python.org/downloads/source/",
) -> list[LongVersion]:
    longs = defaultdict[ShortVersion, list[LongVersion]](list)
    async for long in _iter_python_version(source_uri):
        longs[long.as_short()].append(long)
    return [max(longs[short]) for short in sorted(longs.keys() & set(shorts))]


async def _iter_python_version(
    source_uri: str = "https://www.python.org/downloads/source/",
) -> AsyncGenerator[LongVersion, None]:
    pattern = re.compile(
        r"https?://www\.python\.org/ftp/python/\d+\.\d+\.\d+/"
        r"Python\-(\d+\.\d+\.\d+).tgz",
    )

    async with AsyncExitStack() as stack:
        session = await stack.enter_async_context(ClientSession())
        response = await stack.enter_async_context(session.get(source_uri))

        tree = lxml.html.fromstring(await response.text())

        for href in tree.xpath("//a/@href"):
            if (matched := pattern.match(href)) is not None:
                for group in matched.groups():
                    yield LongVersion.parse(group)


async def categorize_by_ubuntu_release(
    images: Iterable[str],
) -> dict[str, list[str]]:
    ubuntu_images = ChainMap[str, str](
        *await gather(*map(_get_ubuntu_image, images))
    )
    result = defaultdict[str, list[str]](list)
    for image, ubuntu in ubuntu_images.items():
        result[ubuntu].append(image)

    return dict(result)


async def _get_ubuntu_image(image: str) -> dict[str, str]:
    async with terminating(
        await create_subprocess_exec(
            "docker",
            "run",
            image,
            "cat",
            "/etc/lsb-release",
            stdout=PIPE,
        )
    ) as process:
        stdout, _ = await process.communicate()

        if (
            matched := re.search(
                r"DISTRIB_RELEASE=(\d+\.\d+)", stdout.decode("utf-8")
            )
        ) is not None:
            release = matched.group(1)
            return {image: f"ubuntu:{release}"}

    raise ValueError(image)
