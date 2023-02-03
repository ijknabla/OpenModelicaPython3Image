import enum
import re
from collections.abc import Hashable
from functools import lru_cache, total_ordering
from typing import NamedTuple, NewType, Protocol, TypedDict

DistroName = NewType("DistroName", str)
ModelicaVersionString = NewType("ModelicaVersionString", str)
ShortVersionString = NewType("ShortVersionString", str)


class Setting(TypedDict):
    py: list[ShortVersionString]
    omc: list[ShortVersionString]
    distro: list[DistroName]


@total_ordering
class Level(enum.Enum):
    alpha = enum.auto()
    beta = enum.auto()
    final = enum.auto()

    def __lt__(self, other: "Level") -> bool:
        return self.value < other.value


class Release(NamedTuple):
    level: Level = Level.alpha
    version: int = 0

    @property
    def omc_repr(self) -> str:
        match self:
            case (Level.alpha, v):
                return f"~dev.alpha{v}"
            case (Level.beta, v):
                return f"~dev.beta{v}"
            case (Level.final, _):
                return ""
            case _:
                raise NotImplementedError()


class VersionTuple(NamedTuple):
    major: int
    minor: int
    micro: int = 0
    release: Release = Release()
    serial: int = 0

    @property
    def omc_repr(self) -> ModelicaVersionString:
        return ModelicaVersionString(
            f"{self.major}.{self.minor}.{self.micro}"
            f"{self.release.omc_repr}-{self.serial}"
        )


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


class Debian(enum.Enum):
    stretch = enum.auto()
    buster = enum.auto()
    bullseye = enum.auto()

    def __str__(self) -> str:
        assert isinstance(self.name, str)
        return self.name
