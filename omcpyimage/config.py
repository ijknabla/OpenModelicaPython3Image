import re
from typing import Annotated, NamedTuple

from pydantic import BaseModel, PlainSerializer, PlainValidator


class ShortVersion(NamedTuple):
    major: int
    minor: int


@PlainValidator
def _validate_short_version(v: ShortVersion | str) -> ShortVersion:
    if isinstance(v, ShortVersion):
        return v
    if isinstance(v, str):
        if (matched := re.match(r"(\d+)\.(\d+)", v)) is None:
            raise ValueError(v)
        return ShortVersion(*map(int, matched.groups()))

    raise ValueError(v)


@PlainSerializer
def _serialize_short_version(v: ShortVersion) -> str:
    return f"{v.major}.{v.minor}"


AnnotatedShortVersion = Annotated[
    ShortVersion, _validate_short_version, _serialize_short_version
]


class LongVersion(NamedTuple):
    major: int
    minor: int
    patch: int


@PlainValidator
def _validate_long_version(v: LongVersion | str) -> LongVersion:
    if isinstance(v, LongVersion):
        return v
    if isinstance(v, str):
        if (matched := re.match(r"(\d+)\.(\d+)\.(\d+)", v)) is None:
            raise ValueError(v)
        return LongVersion(*map(int, matched.groups()))

    raise ValueError(v)


@PlainSerializer
def _serialize_long_version(v: ShortVersion) -> str:
    return f"{v.major}.{v.minor}"


AnnotatedLongVersion = Annotated[
    LongVersion, _validate_long_version, _serialize_long_version
]


class Config(BaseModel):
    openmodelica: list[AnnotatedLongVersion]
    python: list[AnnotatedShortVersion]
