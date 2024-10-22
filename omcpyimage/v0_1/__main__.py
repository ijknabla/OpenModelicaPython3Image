from __future__ import annotations

import re
import sys
from asyncio import run
from asyncio.subprocess import PIPE, create_subprocess_exec
from functools import wraps
from importlib.resources import as_file, files
from itertools import chain
from typing import IO, TYPE_CHECKING

import click

from . import Version, format_openmodelica_stage

if TYPE_CHECKING:
    from collections.abc import Sequence

    from . import OMVersion


@click.group()
def main() -> None: ...


@main.command()
@click.option("--openmodelica", "--om", multiple=True, type=Version.parse)
@click.option(
    "--output", type=click.File("w", encoding="utf-8", lazy=True), default=sys.stdout
)
def dockerfile(openmodelica: Sequence[OMVersion], output: IO[str]) -> None:
    print(f"{openmodelica=!r}", file=sys.stderr)

    output.write(
        "\n\n".join(
            chain(
                (format_openmodelica_stage(version=om) for om in openmodelica),
            )
        )
    )


@main.command()
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def build() -> None:
    writing_image = re.compile(r"writing image sha256:(?P<sha256>[0-9a-f]{64})")

    images = list[str]()

    with as_file(files(__package__)) as directory:
        target = "v1.24.0-python3.12.7"
        docker_build = await create_subprocess_exec(
            "docker",
            "build",
            f"{directory}",
            f"--target={target}",
            f"-tijknabla/openmodelica:{target}",
            stderr=PIPE,
        )
        if docker_build.stderr is None:
            raise RuntimeError
        async for _line in docker_build.stderr:
            line = _line.decode("utf-8")
            print(line, end="", file=sys.stderr)
            if matched := writing_image.search(line):
                images.append(matched.group("sha256"))

    print("=" * 79)
    for image in images:
        print(f"docker run -it {image}")
    print("=" * 79)

    sys.exit(docker_build.returncode)


if __name__ == "__main__":
    main()
