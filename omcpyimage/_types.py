import enum
import re
from collections.abc import Hashable
from dataclasses import dataclass
from functools import lru_cache, total_ordering
from typing import NamedTuple, NewType, Protocol, TypedDict

DistroName = NewType("DistroName", str)
OMCVersionString = NewType("OMCVersionString", str)
VersionString = str

MODELICA_VERSION_PATTERN = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<micro>\d+)"
    r"(~dev\.alpha(?P<alpha>\d+)|~dev\.beta(?P<beta>\d+)|)"
    r"\-(?P<serial>\d+)"
)


class Setting(TypedDict):
    py: list[VersionString]
    omc: list[VersionString]
    distro: list[DistroName]


@total_ordering
class Level(enum.Enum):
    alpha = enum.auto()
    beta = enum.auto()
    final = enum.auto()

    def __lt__(self, other: "Level") -> bool:
        return self.value < other.value


class Release(NamedTuple):
    level: Level = Level.final
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


@dataclass(frozen=True)
class Version:
    major: int
    minor: int

    def __str__(self) -> VersionString:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True)
class OMCVersion(Version):
    micro: int = 0
    release: Release = Release()
    serial: int = 0

    @property
    def omc_repr(self) -> OMCVersionString:
        return OMCVersionString(
            f"{self.major}.{self.minor}.{self.micro}"
            f"{self.release.omc_repr}-{self.serial}"
        )

    @classmethod
    def parse_omc(cls, s: OMCVersionString) -> "OMCVersion":
        match = MODELICA_VERSION_PATTERN.match(s)
        if match is None:
            raise ValueError(
                f"{s!r} does not match {MODELICA_VERSION_PATTERN.pattern}"
            )
        match match.groups():
            case major, minor, micro, _, None, None, serial:
                return cls(
                    major=int(major),
                    minor=int(minor),
                    micro=int(micro),
                    serial=int(serial),
                )
            case major, minor, micro, _, alpha, None, serial:
                return cls(
                    major=int(major),
                    minor=int(minor),
                    micro=int(micro),
                    release=Release(level=Level.alpha, version=int(alpha)),
                    serial=int(serial),
                )
            case major, minor, micro, _, None, beta, serial:
                return cls(
                    major=int(major),
                    minor=int(minor),
                    micro=int(micro),
                    release=Release(level=Level.beta, version=int(beta)),
                    serial=int(serial),
                )
        raise NotImplementedError()


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
