from __future__ import annotations

import re
from collections.abc import Iterator
from enum import Enum, auto
from functools import total_ordering
from typing import Any, Self

from pydantic import ConfigDict, NonNegativeInt, RootModel, model_validator


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
