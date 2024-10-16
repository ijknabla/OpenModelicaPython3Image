from __future__ import annotations

import re
from asyncio import Future, gather
from asyncio.subprocess import PIPE
from collections import ChainMap, defaultdict
from collections.abc import Iterable
from pathlib import Path
from subprocess import CalledProcessError, Popen
from typing import NamedTuple

import lxml.html
import requests
from pkg_resources import resource_filename

from .types import LongVersion, ShortVersion
from .util import in_executor, terminating


class OpenmodelicaPythonImage(NamedTuple):
    base: str
    ubuntu: str
    openmodelica: str
    python: LongVersion

    @property
    def openmodelica_version(self) -> LongVersion:
        return LongVersion.parse(self.openmodelica)

    @property
    def tag(self) -> str:
        openmodelica = LongVersion.parse(self.openmodelica)
        return f"v{openmodelica}-python{self.python.as_short()}"

    @property
    def image(self) -> str:
        return f"{self.base}:{self.tag}"

    @property
    def pull(self) -> tuple[str, ...]:
        return "docker", "pull", self.image

    def push(self) -> Future[None]:
        return _run("docker", "push", self.image)

    def build(self) -> Future[None]:
        dockerfile = Path(resource_filename(__name__, "Dockerfile")).resolve()
        return _run(
            "docker",
            "build",
            f"{dockerfile.parent}",
            f"--tag={self.image}",
            f"--build-arg=BUILD_IMAGE={self.ubuntu}",
            f"--build-arg=OPENMODELICA_IMAGE={self.openmodelica}",
            f"--build-arg=PYTHON_VERSION={self.python}",
        )


async def search_python_versions(
    shorts: Iterable[ShortVersion],
    source_uri: str = "https://www.python.org/downloads/source/",
) -> list[LongVersion]:
    longs = defaultdict[ShortVersion, list[LongVersion]](list)
    for long in await _iter_python_version(source_uri):
        longs[long.as_short()].append(long)
    return [max(longs[short]) for short in sorted(longs.keys() & set(shorts))]


@in_executor
def _iter_python_version(
    source_uri: str = "https://www.python.org/downloads/source/",
) -> list[LongVersion]:
    pattern = re.compile(
        r"https?://www\.python\.org/ftp/python/\d+\.\d+\.\d+/"
        r"Python\-(\d+\.\d+\.\d+).tgz",
    )

    response = requests.get(source_uri)
    tree = lxml.html.fromstring(response.text)

    return [
        LongVersion.parse(group)
        for href in tree.xpath("//a/@href")
        if (matched := pattern.match(href)) is not None
        for group in matched.groups()
    ]


async def categorize_by_ubuntu_release(
    images: Iterable[str],
) -> dict[str, list[str]]:
    ubuntu_images = ChainMap[str, str](*await gather(*map(_get_ubuntu_image, images)))
    result = defaultdict[str, list[str]](list)
    for image, ubuntu in ubuntu_images.items():
        result[ubuntu].append(image)

    return dict(result)


@in_executor
def _get_ubuntu_image(image: str) -> dict[str, str]:
    with terminating(
        Popen(
            [
                "docker",
                "run",
                image,
                "cat",
                "/etc/lsb-release",
            ],
            stdout=PIPE,
        )
    ) as process:
        if process.stdout is not None:
            for line in process.stdout:
                for matched in re.finditer(rb"DISTRIB_RELEASE=(\d+\.\d+)", line):
                    release = matched.group(1).decode("utf-8")
                    return {image: f"ubuntu:{release}"}

    raise ValueError(image)


@in_executor
def _run(*cmd: str) -> None:
    with terminating(Popen(cmd)) as process:
        process.wait()

    if returncode := process.wait():
        raise CalledProcessError(returncode, cmd)
