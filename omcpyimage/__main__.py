from __future__ import annotations

import asyncio
import logging
import shutil
from asyncio import Lock, TimeoutError, gather, wait_for
from collections.abc import (
    AsyncGenerator,
    Callable,
    Coroutine,
    Iterable,
    Iterator,
    Sequence,
)
from contextlib import AsyncExitStack, asynccontextmanager
from functools import partial, wraps
from itertools import chain
from operator import attrgetter, itemgetter
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from typing import IO, Any, ClassVar, ParamSpec, TypeVar, TypeVarTuple

import click
import tomllib
from git import GitError, Repo
from pydantic import BaseModel

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

        openmodelica_stage = {
            version: OpenModelicaStage(
                stage=f"openmodelica-v{version}",
                version=version,
                source=source.relative_to(cache_dir),
            )
            for version, source in download_openmodelica(
                cache_dir,
                "https://github.com/OpenModelica/OpenModelica.git",
                config.openmodelica,
            )
        }

        dockerfile = cache_dir / "Dockerfile"
        with dockerfile.open("w", encoding="utf-8") as f:
            for stage in openmodelica_stage.values():
                stage.write_dockerfile(f)

        run(
            [
                "docker",
                "build",
                *chain.from_iterable(
                    ["--target", stage, "-t", f"test-{stage}"]
                    for stage in map(attrgetter("stage"), openmodelica_stage.values())
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

        for cmake_lists_txt in source.rglob("CMakeLists.txt"):
            original = cmake_lists_txt.read_text(encoding="utf-8")

            replaced = original.replace(
                "https://build.openmodelica.org/omc/bootstrap/sources.tar.gz",
                "https://build.openmodelica.org/old/bootstrap/sources.tar.gz",
            )

            if replaced != original:
                print(f"Overwrite {cmake_lists_txt}")
                cmake_lists_txt.write_text(replaced, encoding="utf-8")

        yield version, source


class OpenModelicaStage(BaseModel):
    stage: str
    version: LongVersion
    source: Path
    v1_22: ClassVar[LongVersion] = LongVersion(1, 22, 0)

    def write_dockerfile(self, dockerfile: IO[str]) -> None:
        print_ = partial(print, file=dockerfile, flush=False)

        print_(f"FROM ubuntu:latest AS {self.stage}")
        print_("RUN " + " && ".join([" ".join(cmd) for cmd in self.build_dep]))
        print_(f"COPY {self.source} /root")
        print_("RUN " + " && ".join([" ".join(cmd) for cmd in self.build]))

    @property
    def build_dep(self) -> Sequence[Sequence[str]]:
        gcc_alternatives: tuple[str, ...] = ()
        cmake_install: tuple[tuple[str, ...], ...] = ()

        if self.version < self.v1_22:
            gcc_alternatives = ("gcc-12 g++-12",)
            cmake_install = (
                (
                    """\
curl https://cmake.org/files/v3.22/cmake-3.22.1-linux-x86_64.tar.gz --output -\
 | tar zxvf - -C /opt\
""",
                ),
            )

        return (
            ("apt update",),
            (
                """\
apt install -y --no-install-recommends ca-certificates curl gnupg\
""",
                *gcc_alternatives,
            ),
            (
                """\
curl -fsSL http://build.openmodelica.org/apt/openmodelica.asc\
 | gpg --dearmor -o /usr/share/keyrings/openmodelica-keyring.gpg\
""",
            ),
            (
                """\
echo "deb-src [arch=amd64 signed-by=/usr/share/keyrings/openmodelica-keyring.gpg] https://build.openmodelica.org/apt\
 $(cat /etc/os-release | grep "\\(UBUNTU\\|DEBIAN\\|VERSION\\)_CODENAME" | sort | cut -d= -f 2 | head -1) release"\
 | tee /etc/apt/sources.list.d/openmodelica.list\
""",  # noqa: E501
            ),
            ("apt update",),
            ("apt build-dep -y openmodelica",),
            *cmake_install,
        )

    @property
    def build(self) -> Sequence[Sequence[str]]:
        cmake = "cmake"
        gcc = "gcc"
        gxx = "g++"
        if self.version < self.v1_22:
            cmake = "/opt/cmake-3.22.1-linux-x86_64/bin/cmake"
            gcc = "gcc-12"
            gxx = "g++-12"

        return (
            (
                f"""\
{cmake} -DOM_ENABLE_GUI_CLIENTS=OFF -DOM_USE_CCACHE=OFF\
 -DCMAKE_C_COMPILER={gcc} -DCMAKE_CXX_COMPILER={gxx}\
 -S=/root -B=/root/build\
""",
            ),
            ("make -j4 -C /root/build install",),
        )


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
