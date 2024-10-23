from __future__ import annotations

import re
import sys
from asyncio import gather, run
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections import defaultdict
from functools import wraps
from itertools import chain, product
from subprocess import CalledProcessError
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
@click.option("--openmodelica", "--om", multiple=True, type=Version.parse)
@click.option("--python", "--py", multiple=True, type=Version.parse)
@click.option("--check/--no-check", default=False)
@click.option("--push/--no-push", default=False)
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def build(
    openmodelica: Sequence[OMVersion],
    python: Sequence[PyVersion],
    check: bool,
    push: bool,
) -> None:
    stage = [
        Stage(om=om, py=py)
        for om, py in product(
            sorted(set(openmodelica), key=lambda x: x.tuple),
            sorted(set(python), key=lambda x: x.tuple),
        )
    ]
    tags = defaultdict[Stage, list[str]](lambda: [])
    for s in stage:
        tags[s].append(f"ijknabla/openmodelica:v{s.om!s}-python{s.py!s}")

    naming_to_image = re.compile(r"naming to (?P<image>\S+)")
    image = list[str]()

    docker_build_cmd = (
        "docker",
        "build",
        "-",
        *chain.from_iterable(
            ["--target", f"openmodelica{s.om!s}-python{s.py!s}", "--tag", ",".join(t)]
            for s, t in tags.items()
        ),
    )
    docker_build = await create_subprocess_exec(
        *docker_build_cmd,
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

    if docker_build.returncode:
        raise CalledProcessError(
            returncode=docker_build.returncode, cmd=docker_build_cmd
        )

    print("=" * 79)
    for _image in image:
        print(f"docker run -it {_image}")
    print("=" * 79)

    await gather(*(_post_build(s, t, check=check, push=push) for s, t in tags.items()))


async def _post_build(
    stage: Stage, tags: Sequence[str], *, check: bool, push: bool
) -> None:
    if check or push:
        script = f"""\
import sys
assert sys.version.startswith("{stage.py!s}")
from logging import *
from omc4py import *
logger=getLogger("omc4py")
logger.addHandler(StreamHandler())
logger.setLevel(DEBUG)
s=open_session()
assert s.getVersion().startswith(f"v{stage.om!s}")
assert s.installPackage("Modelica")
s.simulate("Modelica.Blocks.Examples.PID_Controller")
s.__check__()
"""
        cmd: tuple[str, ...] = (
            "docker",
            "run",
            tags[0],
            "bash",
            "-c",
            f"python -m pip install openmodelicacompiler && python -c '{script}'",
        )
        docker_run = await create_subprocess_exec(*cmd)
        returncode = await docker_run.wait()
        if returncode:
            raise CalledProcessError(returncode=returncode, cmd=cmd)

    if push:
        for tag in tags:
            cmd = (
                "docker",
                "push",
                tag,
            )
            docker_run = await create_subprocess_exec(*cmd)
            returncode = await docker_run.wait()
            if returncode:
                raise CalledProcessError(returncode=returncode, cmd=cmd)


if __name__ == "__main__":
    main()
