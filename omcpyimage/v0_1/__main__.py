from __future__ import annotations

import re
import sys
from asyncio import run
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections import defaultdict
from functools import wraps
from itertools import chain, product
from typing import IO, TYPE_CHECKING

import click

from . import Stage, Version, format_dockerfile

if TYPE_CHECKING:
    from collections.abc import Sequence

    from . import OMVersion, PyVersion


@click.group()
def main() -> None: ...


@main.command()
@click.option("--openmodelica", "--om", multiple=True, type=Version.parse)
@click.option("--python", "--py", multiple=True, type=Version.parse)
@click.option(
    "--output", type=click.File("w", encoding="utf-8", lazy=True), default=sys.stdout
)
def dockerfile(
    openmodelica: Sequence[OMVersion],
    python: Sequence[PyVersion],
    output: IO[str],
) -> None:
    print(f"{openmodelica=!r}", file=sys.stderr)
    print(f"{python=!r}", file=sys.stderr)
    stage = [
        Stage(om=om, py=py)
        for om, py in product(
            sorted(set(openmodelica), key=lambda x: x.tuple),
            sorted(set(python), key=lambda x: x.tuple),
        )
    ]
    output.write(format_dockerfile(stage))


@main.command()
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def build() -> None:
    stage = [Stage.model_validate({"om": "1.24.0", "py": "3.12.7"})]
    tags = defaultdict[Stage, list[str]](lambda: [])
    for s in stage:
        tags[s].append(f"ijknabla:openmodelicav{s.om!s}-python{s.py!s}")

    naming_to_image = re.compile(r"naming to (?P<image>\S+)")
    image = list[str]()

    docker_build = await create_subprocess_exec(
        "docker",
        "build",
        "-",
        *chain.from_iterable(
            ["--target", f"openmodelica{s.om!s}-python{s.py!s}", "-t", ",".join(t)]
            for s, t in tags.items()
        ),
        stdin=PIPE,
        stderr=PIPE,
    )
    if docker_build.stdin is None or docker_build.stderr is None:
        raise RuntimeError

    docker_build.stdin.write(format_dockerfile(stage).encode("utf-8"))
    docker_build.stdin.write_eof()

    async for _line in docker_build.stderr:
        line = _line.decode("utf-8")
        print(line, end="", file=sys.stderr)
        if matched := naming_to_image.search(line):
            image.append(matched.group("image"))

    print("=" * 79)
    for _image in image:
        print(f"docker run -it {_image}")
    print("=" * 79)

    sys.exit(docker_build.returncode)


if __name__ == "__main__":
    main()
