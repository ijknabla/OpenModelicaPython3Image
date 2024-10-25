from __future__ import annotations

from asyncio import gather
from asyncio.subprocess import PIPE, Process, create_subprocess_exec
from contextlib import AsyncExitStack, asynccontextmanager
from functools import total_ordering, wraps
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, NewType, ParamSpec

from pydantic import BaseModel, ConfigDict

from .version import Version

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Coroutine, Sequence
    from contextlib import AbstractAsyncContextManager
    from typing import Any, Self

P = ParamSpec("P")


@total_ordering
class Image(BaseModel):
    model_config = ConfigDict(frozen=True)

    om: OMVersion
    py: PyVersion

    def __lt__(self, other: Self) -> bool:
        return self.om < other.om or self.py < other.py

    @property
    def docker_build_arg(self) -> tuple[str, ...]:
        return (
            "--build-arg",
            f"OM_MAJOR={self.om.major}",
            "--build-arg",
            f"OM_MINOR={self.om.minor}",
            "--build-arg",
            f"OM_PATCH={self.om.patch}",
            "--build-arg",
            f"PY_MAJOR={self.py.major}",
            "--build-arg",
            f"PY_MINOR={self.py.minor}",
            "--build-arg",
            f"PY_PATCH={self.py.patch}",
        )

    async def deploy(
        self, dockerfile: bytes, tags: Sequence[str], *, push: bool
    ) -> None:
        async with AsyncExitStack() as stack:
            docker_build = await stack.enter_async_context(
                _create2open(create_subprocess_exec)(
                    "docker",
                    "build",
                    *self.docker_build_arg,
                    "-",
                    "--target=final",
                    *(f"--tag={tag}" for tag in tags),
                    stdin=PIPE,
                )
            )
            if docker_build.stdin is None:
                raise RuntimeError

            docker_build.stdin.write(dockerfile)
            docker_build.stdin.write_eof()

            await docker_build.wait()

            check = await stack.enter_async_context(
                _create2open(create_subprocess_exec)(
                    "docker", "run", tags[0], *self._check_command
                )
            )
            if await check.wait():
                return

            if push:
                await gather(
                    *[
                        (
                            await stack.enter_async_context(
                                _create2open(create_subprocess_exec)(
                                    "docker", "push", tag
                                )
                            )
                        ).wait()
                        for tag in tags
                    ]
                )

    @property
    def _check_command(self) -> tuple[str, ...]:
        script = f"""\
import sys
from logging import *
from omc4py import *
from pathlib import *

assert sys.version.startswith("{self.py!s}"), "Check Python version"

logger=getLogger("omc4py")
logger.addHandler(StreamHandler())
logger.setLevel(DEBUG)
s=open_session()

version = s.getVersion(); s.__check__()
assert version.startswith(f"v{self.om!s}"), "Check OpenModelica version"

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


OMVersion = NewType("OMVersion", "Version")
PyVersion = NewType("PyVersion", "Version")


def _create2open(
    f: Callable[P, Coroutine[Any, Any, Process]],
) -> Callable[P, AbstractAsyncContextManager[Process]]:
    @wraps(f)
    @asynccontextmanager
    async def wrapped(*cmd: P.args, **kwargs: P.kwargs) -> AsyncIterator[Process]:
        process = await f(*cmd, **kwargs)
        try:
            yield process
            if process.returncode:
                raise CalledProcessError(process.returncode, cmd)  # type: ignore [arg-type]
        finally:
            match process.returncode:
                case None:
                    process.terminate()
                    await process.wait()

    return wrapped
