import re
from functools import lru_cache
from typing import Any

from schema import And, Schema

from ._decorators import schema2checker
from ._types import DistroName, Setting, ShortVersionString

SHORT_VERSION_PATTERN = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)$")


@schema2checker(Any, Setting)
def is_setting() -> Schema:
    return _setting_schema()


@schema2checker(Any, ShortVersionString)
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


@lru_cache(1)
def _short_version_string_schema() -> Schema:
    def match_short_version_pattern(s: str) -> bool:
        return SHORT_VERSION_PATTERN.match(s) is not None

    return Schema(And(str, match_short_version_pattern))


@lru_cache(1)
def _distro_name_schema() -> Schema:
    return Schema(And(str, len))
