from __future__ import annotations

import re
from asyncio import subprocess
from collections.abc import AsyncIterator, Sequence
from importlib.resources import as_file, files
from typing import NewType, Self

from pydantic import BaseModel, ConfigDict

_URI = NewType("_URI", str)
_Tag = NewType("_Tag", str)
_TargetName = NewType("_TargetName", str)

OPENMODELICA_URI = "https://github.com/OpenModelica/OpenModelica.git"
PYTHON_URI = "https://github.com/python/cpython.git"


async def iter_tags_in_remote(uri: _URI) -> AsyncIterator[_Tag]:
    process = await subprocess.create_subprocess_exec(
        "git", "ls-remote", "--tags", uri, stdout=subprocess.PIPE
    )
    if process.stdout is None:
        raise RuntimeError
    async for buffer in process.stdout:
        for matched in re.finditer(rb"[a-z0-9]{40}\s+(?P<tag>\S+)", buffer):
            yield _Tag(matched.group("tag").decode("ascii"))


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
