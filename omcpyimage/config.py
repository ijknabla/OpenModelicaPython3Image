import re
from typing import Annotated, NamedTuple

from pydantic import BaseModel, Field, PlainSerializer, PlainValidator


class ShortVersion(NamedTuple):
    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


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


class Config(BaseModel):
    from_: list[str] = Field(alias="from")
    python: list[AnnotatedShortVersion]
