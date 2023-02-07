import enum
import logging
import re
from collections.abc import Hashable
from dataclasses import dataclass
from functools import lru_cache, total_ordering
from logging import Logger
from typing import NewType, Protocol, TypedDict

DebianName = NewType("DebianName", str)
OMCVersionString = str
VersionString = str


class Verbosity(enum.Enum):
    SILENT = logging.WARNING
    SLIGHTLY_VERBOSE = logging.INFO
    VERBOSE = logging.DEBUG

    def log(self, logger: Logger, message: str) -> None:
        logger.log(self.value, message)


class Config(TypedDict):
    omc: list[VersionString]
    py: list[VersionString]
    debian: list[DebianName]


@dataclass(order=True, frozen=True)
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


@dataclass(order=True, frozen=True)
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


class Python(enum.Enum):
    v3_7 = enum.auto()
    v3_11 = enum.auto()

    __str__ = _enum2version


@total_ordering
class Debian(enum.Enum):
    stretch = enum.auto()
    buster = enum.auto()
    bullseye = enum.auto()

    @classmethod
    def is_valid_name(cls, name: DebianName) -> bool:
        return name in cls._member_map_

    def __str__(self) -> str:
        assert isinstance(self.name, str)
        return self.name

    def __lt__(self, other: "Debian") -> bool:
        return self.value < other.value


class OMCPackage(enum.Enum):
    libomc = enum.auto()
    libomcsimulation = enum.auto()
    omc = enum.auto()
    omc_common = enum.auto()

    def __str__(self) -> str:
        assert isinstance(self.name, str)
        return self.name.replace("_", "-")

    @property
    def architecture(self) -> str:
        if self is OMCPackage.omc_common:
            return "all"
        else:
            return "amd64"

    def get_uri(self, debian: Debian, version: OMCVersion) -> str:
        return (
            f"https://build.openmodelica.org/apt/pool/contrib-{debian}/"
            f"{self}_{version}_{self.architecture}.deb"
        )
