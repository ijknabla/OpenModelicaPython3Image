from __future__ import annotations

import re
from asyncio import Task, gather, wait
from asyncio.subprocess import Process, create_subprocess_exec
from collections.abc import Coroutine, Iterable, Iterator, Mapping
from contextlib import AsyncExitStack, asynccontextmanager
from enum import Enum, auto
from functools import total_ordering, wraps
from importlib.resources import as_file, files
from subprocess import CalledProcessError
from typing import TYPE_CHECKING, Any, Concatenate, NewType, ParamSpec, Self, TypeVar

from pydantic import BaseModel, ConfigDict, NonNegativeInt, RootModel, model_validator

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable, Coroutine, Sequence
    from contextlib import AbstractAsyncContextManager
    from typing import Any, Self

P = ParamSpec("P")
T = TypeVar("T")


class Application(Enum):
    openmodelica = auto()
    python = auto()


@total_ordering
class Image(BaseModel):
    model_config = ConfigDict(frozen=True)

    om: OMVersion
    py: PyVersion

    @property
    def mapping(self) -> dict[Application, Version]:
        return {Application.openmodelica: self.om, Application.python: self.py}

    def __lt__(self, other: Self) -> bool:
        return self.om < other.om or self.py < other.py

    async def deploy(self, tags: Sequence[str], *, push: bool) -> None:
        async with AsyncExitStack() as stack:
            build = await stack.enter_async_context(
                aopen_subprocess_exec(*build_cmd(self.mapping, tags))
            )
            await build.wait()

            test = await stack.enter_async_context(
                aopen_subprocess_exec(*test_cmd(self.mapping, tags[0]))
            )
            if await test.wait():
                return

            if push:
                await gather(
                    *[
                        (
                            await stack.enter_async_context(
                                aopen_subprocess_exec(*push_cmd(tag))
                            )
                        ).wait()
                        for tag in tags
                    ]
                )


OMVersion = NewType("OMVersion", "Version")
PyVersion = NewType("PyVersion", "Version")


def build_cmd(
    version: Mapping[Application, Version],
    tags: Sequence[str],
) -> tuple[str, ...]:
    with as_file(files(__package__)) as dockerfile:
        om = version[Application.openmodelica]
        py = version[Application.python]
        return (
            "docker",
            "build",
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
            "--target=final",
            *(f"--tag={tag}" for tag in tags),
            dockerfile.__fspath__(),
        )


def test_cmd(version: Mapping[Application, Version], tag: str) -> tuple[str, ...]:
    om = version[Application.openmodelica]
    py = version[Application.python]
    with as_file(files(__package__).joinpath("test.py")) as test_py:
        return (
            "docker",
            "run",
            tag,
            "bash",
            "-c",
            " && ".join(
                [
                    "python -m pip install click openmodelicacompiler",
                    f"python -c '{test_py.read_text(encoding='utf-8')}' "
                    f"--openmodelica-version={om} --python-version={py}",
                ]
            ),
        )


def push_cmd(tag: str) -> tuple[str, ...]:
    return ("docker", "push", tag)


@total_ordering
class Unset(Enum):
    unset = auto()

    def __lt__(self, other: Unset | int, /) -> bool:
        if isinstance(other, int):
            return True
        else:
            return False


unset = Unset.unset


@total_ordering
class Version(
    RootModel[tuple[NonNegativeInt, NonNegativeInt | Unset, NonNegativeInt | Unset]]
):
    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        def item() -> Iterator[str]:
            for i in self.root:
                if i is unset:
                    yield ""
                else:
                    yield f".{i}"

        return "".join(item())[1:]

    def __lt__(self, other: Self, /) -> bool:
        return self.root < other.root

    @property
    def major(self) -> int:
        return self.root[0]

    @property
    def minor(self) -> int | Unset:
        return self.root[1]

    @property
    def patch(self) -> int | Unset:
        return self.root[2]

    @property
    def short(self) -> Self:
        return type(self).model_validate(self.root[:2])

    @model_validator(mode="before")  # type: ignore [arg-type]
    @staticmethod
    def _model_validator(root: Any) -> None:
        if isinstance(root, str):
            target = re.compile(r"(?P<major>\d+)(\.(?P<minor>\d+)(\.(?P<patch>\d+))?)?")
            match target.match(root):
                case None:
                    ValueError(f"{root!r} does not match {target.pattern!r}")
                case matched:
                    root = tuple(
                        int(s)
                        for s in (
                            matched.group("major"),
                            matched.group("minor"),
                            matched.group("patch"),
                        )
                        if s is not None
                    )

        match root:
            case (major,) | (major, None, None):
                return major, unset, unset
            case (major, minor) | (major, minor, None):
                return major, minor, unset
            case (major, minor, patch):
                return major, minor, patch
            case _:
                raise NotImplementedError(root)


def _wrap_as_wait_and_remove(
    f: Callable[
        Concatenate[Iterable[Task[T]], P],
        Coroutine[Any, Any, tuple[set[Task[T]], set[Task[T]]]],
    ],
) -> Callable[Concatenate[set[Task[T]], P], Coroutine[Any, Any, set[Task[T]]]]:
    @wraps(f)
    async def wrapped(
        pending: set[Task[T]], /, *args: P.args, **kwargs: P.kwargs
    ) -> set[Task[T]]:
        done, _ = await f(pending, *args, **kwargs)
        pending -= done
        return done

    return wrapped


wait_and_remove = _wrap_as_wait_and_remove(wait)


def _create2aopen(
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


aopen_subprocess_exec = _create2aopen(create_subprocess_exec)
