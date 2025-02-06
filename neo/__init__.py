import sys
from asyncio import subprocess


async def docker_buildx_bake() -> None:
    process = await subprocess.create_subprocess_exec("docker", "buildx", "bake")
    sys.exit(await process.wait())
