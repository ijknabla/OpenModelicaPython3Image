import sys
from asyncio import subprocess
from importlib.resources import as_file, files

from pydantic import BaseModel


class DockerBake(BaseModel): ...


async def docker_buildx_bake(indent: int | None) -> None:
    with as_file(files(__name__)) as package_directory:
        config = DockerBake.model_validate({})
        (package_directory / "docker-bake.json").write_text(
            config.model_dump_json(indent=indent), encoding="utf-8"
        )

        process = await subprocess.create_subprocess_exec(
            "docker", "buildx", "bake", cwd=package_directory
        )
        sys.exit(await process.wait())
