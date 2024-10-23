from __future__ import annotations

import sys
from asyncio import gather, run
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections import defaultdict
from functools import wraps
from importlib.resources import read_binary
from itertools import product
from subprocess import CalledProcessError
from typing import IO, TYPE_CHECKING

import click

from . import Image, Version, format_dockerfile

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
        Image(om=om, py=py)
        for om, py in product(
            sorted(set(openmodelica), key=lambda x: x.as_tuple),
            sorted(set(python), key=lambda x: x.as_tuple),
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
    image = [
        Image(om=om, py=py)
        for om, py in product(
            sorted(set(openmodelica), key=lambda x: x.as_tuple),
            sorted(set(python), key=lambda x: x.as_tuple),
        )
    ]
    tags = defaultdict[Image, list[str]](lambda: [])
    for im in image:
        tags[im].append(f"ijknabla/openmodelica:v{im.om!s}-python{im.py!s}")

    for im in image:
        cmd = (
            "docker",
            "build",
            *im.docker_build_arg,
            "-",
            # *chain.from_iterable(
            #     [
            #         "--target",
            #         f"openmodelica{s.om!s}-python{s.py!s}",
            #         "--tag",
            #         ",".join(t),
            #     ]
            #     for s, t in tags.items()
            # ),
        )
        docker_build = await create_subprocess_exec(
            *cmd,
            stdin=PIPE,
        )
        if docker_build.stdin is None:
            raise RuntimeError

        docker_build.stdin.write(read_binary(__package__, "Dockerfile"))
        docker_build.stdin.write_eof()

        returncode = await docker_build.wait()
        if returncode:
            raise CalledProcessError(returncode=returncode, cmd=cmd)

    print("=" * 72)
    for _, tt in sorted(tags.items(), key=lambda kv: kv[0].as_tuple):
        for t in tt:
            print(f"- {t}")
    print("=" * 72)

    await gather(*(_post_build(s, t, check=check, push=push) for s, t in tags.items()))


async def _post_build(
    image: Image, tags: Sequence[str], *, check: bool, push: bool
) -> None:
    if check or push:
        script = f"""\
import sys
assert sys.version.startswith("{image.py!s}")
from logging import *
from omc4py import *
logger=getLogger("omc4py")
logger.addHandler(StreamHandler())
logger.setLevel(DEBUG)
s=open_session()
assert s.getVersion().startswith(f"v{image.om!s}")
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
