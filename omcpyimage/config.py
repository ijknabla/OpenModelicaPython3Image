from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer, PlainValidator

from .types import ShortVersion


@PlainValidator
def _validate_short_version(v: ShortVersion | str) -> ShortVersion:
    if isinstance(v, ShortVersion):
        return v
    elif isinstance(v, str):
        return ShortVersion.parse(v)
    else:
        raise ValueError(v)


@PlainSerializer
def _serialize_short_version(v: ShortVersion) -> str:
    return str(v)


AnnotatedShortVersion = Annotated[
    ShortVersion, _validate_short_version, _serialize_short_version
]


class Config(BaseModel):
    from_: list[str] = Field(alias="from")
    python: list[AnnotatedShortVersion]
