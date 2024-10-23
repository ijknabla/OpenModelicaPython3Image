from __future__ import annotations

from asyncio import gather, run
from asyncio.subprocess import create_subprocess_exec
from collections import defaultdict
from functools import wraps
from importlib.resources import read_binary
from itertools import product
from subprocess import CalledProcessError
from typing import TYPE_CHECKING

import click

from . import Image, Version

if TYPE_CHECKING:
    from collections.abc import Sequence

    from . import OMVersion, PyVersion


@click.group()
def main() -> None: ...


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

    dockerfile = read_binary(__package__, "Dockerfile")

    for im in image:
        await im.deploy(dockerfile, tags[im])

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
from logging import *
from omc4py import *
from pathlib import *

assert sys.version.startswith("{image.py!s}"), "Check Python version"

logger=getLogger("omc4py")
logger.addHandler(StreamHandler())
logger.setLevel(DEBUG)
s=open_session()

version = s.getVersion(); s.__check__()
assert version.startswith(f"v{image.om!s}"), "Check OpenModelica version"

installed = s.installPackage("Modelica"); s.__check__()
assert installed, "Install Modelica package"

loaded = s.loadModel("Modelica"); s.__check__()
assert loaded, "Load Modelica package"

result = s.simulate("Modelica.Blocks.Examples.PID_Controller"); s.__check__()
assert "The simulation finished successfully." in result.messages, "Check simulation result"
assert Path(result.resultFile).exists(), "Check simulation output"
"""  # noqa: E501
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
