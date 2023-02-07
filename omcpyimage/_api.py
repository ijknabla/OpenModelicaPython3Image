import re
from contextlib import suppress
from datetime import datetime
from functools import lru_cache
from typing import Any

from schema import And, Schema

from ._decorators import schema2checker
from ._types import Config, Debian, LongVersion, Version


@schema2checker(Any, Config)
def is_config() -> Schema:
    return _config_schema()


def is_version(s: str) -> bool:
    with suppress(ValueError):
        Version.parse(s)
        return True
    return False


def is_long_version(s: str) -> bool:
    with suppress(ValueError):
        LongVersion.parse(s)
        return True
    return False


def is_debian(s: str) -> bool:
    with suppress(KeyError):
        Debian[s]
        return True
    return False


@lru_cache(1)
def _config_schema() -> Schema:
    return Schema(
        {
            "omc": [And(str, is_version)],
            "py": [And(str, is_version)],
            "debian": [And(str, is_debian)],
            "cache": _cache_schema(),
        }
    )


@lru_cache(1)
def _cache_schema() -> Schema:
    return Schema(
        {
            "py-images": Schema(
                {_is_py_image_cache_key: _py_image_cache_schema()}
            )
        }
    )


def _is_py_image_cache_key(s: str) -> bool:
    match = re.match(r"^python:(?P<python>.+?)\-(?P<debian>.+?)$", s)
    if match is None:
        return False

    python, debian = match.groups()
    return is_version(python) and is_debian(debian)


@lru_cache(1)
def _py_image_cache_schema() -> Schema:
    return Schema({"updated-at": datetime, "exists": bool})
