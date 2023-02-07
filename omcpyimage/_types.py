import enum
import re
from collections.abc import Hashable, Iterator
from dataclasses import dataclass
from functools import lru_cache, total_ordering
from typing import ClassVar, Protocol


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
    def parse(cls, s: str) -> "Version":
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


class SupportsName(Hashable, Protocol):
    name: str


@lru_cache(None)
def _enum2version(obj: SupportsName) -> str:
    return ".".join(map(str, _enum2version_tuple(obj)))


@lru_cache(None)
def _enum2version_tuple(obj: SupportsName) -> tuple[int, int]:
    matched = re.match(r"v(\d+)_(\d+)", obj.name)
    assert matched is not None
    major, minor = map(int, matched.groups())
    return major, minor


class OpenModelica(enum.Enum):
    v1_13 = enum.auto()
    v1_14 = enum.auto()
    v1_15 = enum.auto()
    v1_16 = enum.auto()
    v1_17 = enum.auto()
    v1_18 = enum.auto()
    v1_19 = enum.auto()
    v1_20 = enum.auto()

    @property
    def tuple(self) -> tuple[int, int]:
        return _enum2version_tuple(self)


class Python(enum.Enum):
    v3_7 = enum.auto()
    v3_11 = enum.auto()

    __str__ = _enum2version


@total_ordering
class Debian(enum.Enum):
    stretch = enum.auto()
    buster = enum.auto()
    bullseye = enum.auto()

    def __str__(self) -> str:
        assert isinstance(self.name, str)
        return self.name

    def __lt__(self, other: "Debian") -> bool:
        return self.value < other.value
