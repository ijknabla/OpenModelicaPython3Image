from __future__ import annotations

from asyncio.subprocess import PIPE, create_subprocess_exec
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack
from importlib.resources import read_binary

from frozendict import frozendict
from pydantic import BaseModel, ConfigDict

from .. import Version, _create2open
from .constant import Application


class Request(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    version: frozendict[Application, Version]

    async def reply(self) -> AsyncIterator[Response]:
        async with AsyncExitStack() as stack:
            om = self.version[Application.openmodelica]
            py = self.version[Application.python]

            tags = [
                f"ijknabla/openmodelica:v{om!s}-python{py!s}",
                f"ijknabla/openmodelica:v{om.short!s}-python{py.short!s}",
            ]

            docker_build = await stack.enter_async_context(
                _create2open(create_subprocess_exec)(
                    "docker",
                    "build",
                    *(
                        "--build-arg",
                        f"OM_MAJOR={om.major}",
                        "--build-arg",
                        f"OM_MINOR={om.minor}",
                        "--build-arg",
                        f"OM_PATCH={om.patch}",
                        "--build-arg",
                        f"PY_MAJOR={py.major}",
                        "--build-arg",
                        f"PY_MINOR={py.minor}",
                        "--build-arg",
                        f"PY_PATCH={py.patch}",
                    ),
                    "-",
                    "--target=final",
                    *(f"--tag={tag}" for tag in tags),
                    stdin=PIPE,
                )
            )
            if docker_build.stdin is None:
                raise RuntimeError

            docker_build.stdin.write(read_binary("omcpyimage.v0_1", "Dockerfile"))
            docker_build.stdin.write_eof()

            await docker_build.wait()

            check = await stack.enter_async_context(
                _create2open(create_subprocess_exec)(
                    "docker", "run", tags[0], *_check_command(om=om, py=py)
                )
            )

            await check.wait()

        yield Response()


class Response(BaseModel): ...


def _check_command(om: Version, py: Version) -> tuple[str, ...]:
    script = f"""\
import sys
from logging import *
from omc4py import *
from pathlib import *

assert sys.version.startswith("{py!s}"), "Check Python version"

logger=getLogger("omc4py")
logger.addHandler(StreamHandler())
logger.setLevel(DEBUG)
s=open_session()

version = s.getVersion(); s.__check__()
assert version.startswith(f"v{om!s}"), "Check OpenModelica version"

installed = s.installPackage("Modelica"); s.__check__()
assert installed, "Install Modelica package"

loaded = s.loadModel("Modelica"); s.__check__()
assert loaded, "Load Modelica package"

result = s.simulate("Modelica.Blocks.Examples.PID_Controller"); s.__check__()
assert \
    "The simulation finished successfully." in result.messages, \
    "Check simulation result"
assert Path(result.resultFile).exists(), "Check simulation output"
"""
    return (
        "bash",
        "-c",
        f"python -m pip install openmodelicacompiler && python -c '{script}'",
    )
