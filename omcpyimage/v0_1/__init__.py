from __future__ import annotations

import re
from asyncio.subprocess import PIPE, Process, create_subprocess_exec
from contextlib import AsyncExitStack, asynccontextmanager
from functools import wraps
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, NewType, ParamSpec

from pydantic import BaseModel, ConfigDict, StrictInt, model_validator

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Coroutine, Sequence
    from contextlib import AbstractAsyncContextManager
    from typing import Any, Self

P = ParamSpec("P")


class Image(BaseModel):
    model_config = ConfigDict(frozen=True)

    om: OMVersion
    py: PyVersion

    @property
    def as_tuple(self) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        return self.om.as_tuple, self.py.as_tuple

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

    async def deploy(self, dockerfile: bytes, tags: Sequence[str]) -> None:
        async with AsyncExitStack() as stack:
            docker_build = await stack.enter_async_context(
                _create2open(create_subprocess_exec)(
                    "docker",
                    "build",
                    *self.docker_build_arg,
                    "-",
                    "--target=final",
                    "--tag",
                    ",".join(tags),
                    stdin=PIPE,
                )
            )
            if docker_build.stdin is None:
                raise RuntimeError

            docker_build.stdin.write(dockerfile)
            docker_build.stdin.write_eof()

            await docker_build.wait()


OMVersion = NewType("OMVersion", "Version")
PyVersion = NewType("PyVersion", "Version")


class Version(BaseModel):
    model_config = ConfigDict(frozen=True)

    major: StrictInt
    minor: StrictInt
    patch: StrictInt

    @classmethod
    def parse(cls, s: str, /, *, strict: bool = True) -> Self:
        pattern = r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        if strict:
            matched = re.match(rf"^{pattern}$", s)
        else:
            matched = re.search(pattern, s)
        if matched is None:
            raise ValueError(s)
        return cls(
            major=int(matched.group("major")),
            minor=int(matched.group("minor")),
            patch=int(matched.group("patch")),
        )

    @property
    def short(self) -> ShortVersion:
        return ShortVersion(major=self.major, minor=self.minor)

    @property
    def as_tuple(self) -> tuple[int, int, int]:
        return self.major, self.minor, self.patch

    def __str__(self) -> str:
        return ".".join(map(str, self.as_tuple))

    @model_validator(mode="before")  # type: ignore [arg-type]
    @classmethod
    def _model_validate(cls, obj: Any, /) -> Any:
        if isinstance(obj, str):
            return cls.parse(obj, strict=True).model_dump()
        return obj


class ShortVersion(BaseModel):
    model_config = ConfigDict(frozen=True)

    major: StrictInt
    minor: StrictInt

    @property
    def as_tuple(self) -> tuple[int, int]:
        return self.major, self.minor

    def __str__(self) -> str:
        return ".".join(map(str, self.as_tuple))


def _create2open(
    f: Callable[P, Coroutine[Any, Any, Process]],
) -> Callable[P, AbstractAsyncContextManager[Process]]:
    @wraps(f)
    @asynccontextmanager
    async def wrapped(*cmd: P.args, **kwargs: P.kwargs) -> AsyncIterator[Process]:
        process = await f(*cmd, **kwargs)
        try:
            yield process
        finally:
            match process.returncode:
                case 0:
                    return
                case None:
                    process.terminate()
                    await process.wait()
                case returncode:
                    raise CalledProcessError(returncode, cmd)  # type: ignore [arg-type]

    return wrapped
