from typing import Annotated

from pydantic import BaseModel, PlainSerializer, PlainValidator

from .types import LongVersion, ShortVersion


@PlainValidator
def _validate_long_version(v: LongVersion | str) -> LongVersion:
    if isinstance(v, LongVersion):
        return v
    elif isinstance(v, str):
        return LongVersion.parse(v)
    else:
        raise ValueError(v)


@PlainValidator
def _validate_short_version(v: ShortVersion | str) -> ShortVersion:
    if isinstance(v, ShortVersion):
        return v
    elif isinstance(v, str):
        return ShortVersion.parse(v)
    else:
        raise ValueError(v)


@PlainSerializer
def _serialize_long_version(v: LongVersion) -> str:
    return str(v)


@PlainSerializer
def _serialize_short_version(v: ShortVersion) -> str:
    return str(v)


AnnotatedLongVersion = Annotated[
    LongVersion, _validate_long_version, _serialize_long_version
]
AnnotatedShortVersion = Annotated[
    ShortVersion, _validate_short_version, _serialize_short_version
]


class Config(BaseModel):
    openmodelica: list[AnnotatedLongVersion]
    python: list[AnnotatedShortVersion]
