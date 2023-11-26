from asyncio import create_subprocess_exec
from pathlib import Path

from pkg_resources import resource_filename

from .types import LongVersion
from .util import terminating


async def pull(image: str) -> None:
    process = await create_subprocess_exec("docker", "pull", image)
    async with terminating(process):
        assert await process.wait() == 0


async def build(image: str) -> None:
    version = LongVersion.parse(image)
    dockerfile = Path(resource_filename(__name__, "Dockerfile")).resolve()

    process = await create_subprocess_exec(
        "docker",
        "build",
        f"{dockerfile.parent}",
        f"--tag=ijknabla/openmodelica:v{version}-python",
        f"--build-arg=OPENMODELICA_IMAGE={image}",
    )
    async with terminating(process):
        assert await process.wait() == 0
