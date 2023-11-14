import enum
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from functools import total_ordering
from typing import ClassVar, Type, TypedDict, TypeVar


class Config(TypedDict):
    omc: list[str]
    py: list[str]
    debian: list[str]
    cache: "Cache"


Cache = TypedDict("Cache", {"py-images": dict[str, "PyImageCache"]})
PyImageCache = TypedDict(
    "PyImageCache", {"updated-at": datetime, "exists": bool}
)


T_version = TypeVar("T_version", bound="Version")


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int

    __pattern__: ClassVar[re.Pattern[str]] = re.compile(
        r"^(?P<major>\d+)\.(?P<minor>\d+)$"
    )

    def __iter__(self) -> Iterator[int]:
        yield self.major
        yield self.minor

    def __str__(self) -> str:
        return ".".join(map(str, self))

    @classmethod
    def parse(cls: Type[T_version], s: str) -> T_version:
        match = cls.__pattern__.match(s)
        if match is None:
            raise ValueError(f"{s!r} does not match {cls.__pattern__.pattern}")
        return cls(*map(int, match.groups()))


@dataclass(frozen=True, order=True)
class LongVersion(Version):
    micro: int

    __pattern__ = re.compile(
        r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<micro>\d+)$"
    )

    def __iter__(self) -> Iterator[int]:
        yield self.major
        yield self.minor
        yield self.micro

    @property
    def as_short(self) -> Version:
        return Version(major=self.major, minor=self.minor)


@total_ordering
class Debian(enum.Enum):
    stretch = enum.auto()
    buster = enum.auto()
    bullseye = enum.auto()
    bookworm = enum.auto()

    def __str__(self) -> str:
        assert isinstance(self.name, str)
        return self.name

    def __lt__(self, other: "Debian") -> bool:
        return self.value < other.value
