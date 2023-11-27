from asyncio import create_subprocess_exec
from contextlib import AsyncExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from pkg_resources import resource_filename

from .types import LongVersion
from .util import terminating


async def pull(image: str) -> None:
    process = await create_subprocess_exec("docker", "pull", image)
    async with terminating(process):
        assert await process.wait() == 0


async def build(image: str, python: LongVersion) -> str:
    openmodelica = LongVersion.parse(image)
    dockerfile = Path(resource_filename(__name__, "Dockerfile.in")).resolve()

    tag = f"ijknabla/openmodelica:v{openmodelica}-python{python.as_short()}"

    async with AsyncExitStack() as stack:
        directory = Path(stack.enter_context(TemporaryDirectory()))
        (directory / dockerfile.stem).write_text(
            dockerfile.read_text().format(
                OPENMODELICA_IMAGE=image, PYTHON_VERSION=python
            )
        )

        process = await stack.enter_async_context(
            terminating(
                await create_subprocess_exec(
                    "docker",
                    "build",
                    f"{directory}",
                    f"--tag={tag}",
                    f"--build-arg=OPENMODELICA_IMAGE={image}",
                )
            )
        )

        assert await process.wait() == 0

    return tag
