from asyncio import subprocess
from importlib.resources import as_file, files

from pydantic import BaseModel, ConfigDict


class DockerBake(BaseModel):
    model_config = ConfigDict(extra="allow")

    async def build(self, indent: int | None) -> int:
        with as_file(files(__name__)) as package_directory:
            (package_directory / "docker-bake.json").write_text(
                self.model_dump_json(indent=indent), encoding="utf-8"
            )

            process = await subprocess.create_subprocess_exec(
                "docker", "buildx", "bake", cwd=package_directory
            )
            return await process.wait()
