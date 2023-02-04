import re
from functools import lru_cache
from typing import Any

from schema import And, Schema

from ._decorators import schema2checker
from ._types import (
    DistroName,
    OMCVersion,
    OMCVersionString,
    Release,
    Setting,
    Version,
    VersionString,
)


@schema2checker(Any, Setting)
def is_setting() -> Schema:
    return _setting_schema()


@schema2checker(Any, VersionString)
def is_short_version_string() -> Schema:
    return _short_version_string_schema()


@schema2checker(Any, DistroName)
def is_distro_name() -> Schema:
    return _distro_name_schema()


@lru_cache(1)
def _setting_schema() -> Schema:
    return Schema(
        {
            "py": And([_short_version_string_schema()], len),
            "omc": And([_short_version_string_schema()], len),
            "distro": And([_distro_name_schema()], len),
        }
    )


SHORT_VERSION_PATTERN = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)$")


def parse_version(s: VersionString) -> Version:
    match = SHORT_VERSION_PATTERN.match(s)
    if match is None:
        raise ValueError(
            f"{s!r} does not match {SHORT_VERSION_PATTERN.pattern}"
        )
    major, minor = match.groups()
    return Version(major=int(major), minor=int(minor))


@lru_cache(1)
def _short_version_string_schema() -> Schema:
    def match_short_version_pattern(s: str) -> bool:
        return SHORT_VERSION_PATTERN.match(s) is not None

    return Schema(And(str, match_short_version_pattern))


MODELICA_VERSION_PATTERN = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<micro>\d+)"
    r"(~dev\.alpha(?P<alpha>\d+)|~dev\.beta(?P<beta>\d+)|)"
    r"\-(?P<build>\d+)"
)


def parse_omc_version(s: OMCVersionString) -> OMCVersion:
    match = MODELICA_VERSION_PATTERN.match(s)
    if match is None:
        raise ValueError(
            f"{s!r} does not match {MODELICA_VERSION_PATTERN.pattern}"
        )
    major = int(match.group("major"))
    minor = int(match.group("minor"))
    micro = int(match.group("micro"))
    release: Release
    build = int(match.group("build"))
    stage: int | None
    match match.group("alpha"), match.group("beta"):
        case None, None:
            release = Release.final
            stage = None
        case alpha, None:
            release = Release.alpha
            stage = int(alpha)
        case None, beta:
            release = Release.beta
            stage = int(beta)
        case _:
            raise NotImplementedError()

    return OMCVersion(
        major=major,
        minor=minor,
        micro=micro,
        release=release,
        stage=stage,
        build=build,
    )


@lru_cache(1)
def _distro_name_schema() -> Schema:
    return Schema(And(str, len))
