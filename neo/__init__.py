from __future__ import annotations

from asyncio import subprocess
from collections.abc import Sequence
from importlib.resources import as_file, files
from typing import NewType, Self

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

    @classmethod
    def from_targets(cls, targets: Sequence[Target]) -> Self:
        return cls.model_validate(
            {
                "group": {"default": {"targets": [x.name for x in targets]}},
                "target": {
                    x.name: {
                        "context": ".",
                        "dockerfile": "Dockerfile",
                        "args": x.args,
                        "tags": [
                            # "myapp:ubuntu", "myapp:latest"
                        ],
                    }
                    for x in targets
                },
            }
        )


_TargetName = NewType("_TargetName", str)


class Target(BaseModel):
    openmodelica: tuple[int, int, int]
    python: tuple[int, int, int]

    @property
    def name(self) -> _TargetName:
        return _TargetName(
            "{}-{}".format(
                "_".join(map(str, self.openmodelica)),
                "_".join(map(str, self.python)),
            )
        )

    @property
    def args(self) -> dict[str, str]:
        OM_MAJOR, OM_MINOR, OM_PATCH = map(str, self.openmodelica)
        PY_MAJOR, PY_MINOR, PY_PATCH = map(str, self.python)
        return dict(
            OM_MAJOR=OM_MAJOR,
            OM_MINOR=OM_MINOR,
            OM_PATCH=OM_PATCH,
            PY_MAJOR=PY_MAJOR,
            PY_MINOR=PY_MINOR,
            PY_PATCH=PY_PATCH,
        )
