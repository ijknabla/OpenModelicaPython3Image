import enum
import re
from functools import lru_cache
from typing import Protocol


class SupportsName(Protocol):
    name: str


@lru_cache(None)
def _enum2version(obj: SupportsName) -> str:
    matched = re.match(r"v(\d+)_(\d+)", obj.name)
    assert matched is not None
    return ".".join(matched.groups())


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
