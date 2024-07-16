from __future__ import annotations

import asyncio
import logging
import shutil
from asyncio import Lock, TimeoutError, gather, wait_for
from collections.abc import AsyncGenerator, Callable, Coroutine, Iterable, Iterator
from contextlib import AsyncExitStack, asynccontextmanager
from functools import partial, wraps
from itertools import chain
from operator import itemgetter
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from typing import IO, Any, ParamSpec, TypeVar, TypeVarTuple

import click
import tomllib
from git import GitError, Repo

from . import builder
from .builder import OpenmodelicaPythonImage
from .config import Config
from .types import LongVersion

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
@click.option(
    "--cache-dir",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
)
@execute_coroutine
async def main(config_io: IO[bytes], cache_dir: Path | None) -> None:
    git_cmd_logger = logging.getLogger("git.cmd")
    git_cmd_logger.setLevel(logging.DEBUG)
    git_cmd_logger.addHandler(logging.StreamHandler())

    config = Config.model_validate(tomllib.load(config_io))

    async with AsyncExitStack() as stack:
        if cache_dir is None:
            cache_dir = Path(stack.enter_context(TemporaryDirectory()))

        openmodelica_stage = {v: f"openmodelica-v{v}" for v in config.openmodelica}
        openmodelica_source = dict(
            download_openmodelica(
                cache_dir,
                "https://github.com/OpenModelica/OpenModelica.git",
                config.openmodelica,
            )
        )

        dockerfile = cache_dir / "Dockerfile"
        with dockerfile.open("w", encoding="utf-8") as f:
            for v in config.openmodelica:
                write_openmodelica_stage(
                    f,
                    openmodelica_stage[v],
                    v,
                    openmodelica_source[v].relative_to(cache_dir),
                )

        run(
            [
                "docker",
                "build",
                *chain.from_iterable(
                    ["--target", stage, "-t", f"test-{stage}"]
                    for stage in openmodelica_stage.values()
                ),
                f"{cache_dir}",
            ],
            env={"DOCKER_BUILDKIT": "1"},
        )

    pythons = await builder.search_python_versions(config.python)

    return

    ubuntu_openmodelica = await builder.categorize_by_ubuntu_release(config.from_)

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

    await gather(*(image.pull() for image in images), return_exceptions=True)
    for group in [group0, group1, group2]:
        await gather(*(image.build() for image in sorted(group)))
    await gather(*(image.push() for image in images))
    for image in sorted(images):
        print(image)


def download_openmodelica(
    directory: Path, uri: str, versions: Iterable[LongVersion]
) -> Iterator[tuple[LongVersion, Path]]:
    repository_path = directory / "OpenModelica/repo"

    try:
        repository = Repo(repository_path)
    except GitError:
        repository = Repo.clone_from(uri, repository_path)

    for version in versions:
        repository.git.checkout(f"v{version}")
        repository.git.clean("-fdx")
        repository.git.submodule("update", "--init", "--recursive")

        source = directory / f"OpenModelica/src/v{version}"

        for relative in repository.git.ls_files("--recurse-submodule").splitlines(
            keepends=False
        ):
            src = Path(repository.git_dir, "..", relative)
            if src.is_file():
                dst = source / relative
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(src, dst)

        yield version, source


def write_openmodelica_stage(
    dockerfile: IO[str], stage: str, version: LongVersion, source: Path
) -> None:
    print_ = partial(print, file=dockerfile, flush=False)

    print_(f"FROM ubuntu:latest AS {stage}")
    print_(f"COPY {source} /root")


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
