import enum
import re
from collections.abc import Hashable
from dataclasses import dataclass
from functools import lru_cache, total_ordering
from typing import NewType, Protocol, TypedDict

DistroName = NewType("DistroName", str)
OMCVersionString = str
VersionString = str


class Setting(TypedDict):
    py: list[VersionString]
    omc: list[VersionString]
    distro: list[DistroName]


@dataclass(frozen=True)
class Version:
    major: int
    minor: int

    def __str__(self) -> VersionString:
        return f"{self.major}.{self.minor}"


@total_ordering
class Release(enum.Enum):
    alpha = enum.auto()
    beta = enum.auto()
    final = enum.auto()

    def __lt__(self, other: "Release") -> bool:
        return self.value < other.value


@dataclass(frozen=True)
class OMCVersion(Version):
    micro: int
    release: Release
    stage: int | None
    build: int

    def __post_init__(self) -> None:
        release = self.release
        stage = self.stage
        match release, stage:
            case Release.alpha, i if isinstance(i, int):
                ...
            case Release.beta, i if isinstance(i, int):
                ...
            case Release.final, None:
                ...
            case _:
                raise ValueError(f"{release=}, {stage=}")

    def __str__(self) -> OMCVersionString:
        match self.release, self.stage:
            case Release.alpha, i:
                release_stage = f"~dev.alpha{i}"
            case Release.beta, i:
                release_stage = f"~dev.beta{i}"
            case Release.final, None:
                release_stage = ""
            case _:
                raise NotImplementedError()

        return (
            f"{self.major}.{self.minor}.{self.micro}"
            f"{release_stage}-{self.build}"
        )

    @property
    def short(self) -> Version:
        return Version(major=self.major, minor=self.minor)


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
