import re
from typing import Annotated, NamedTuple

from pydantic import BaseModel, PlainSerializer, PlainValidator


class Version(NamedTuple):
    major: int
    minor: int


@PlainValidator
def _validate_version(v: Version | str) -> Version:
    if isinstance(v, Version):
        return v
    if isinstance(v, str):
        if (matched := re.match(r"(\d+)\.(\d+)", v)) is None:
            raise ValueError(v)
        return Version(*map(int, matched.groups()))

    raise ValueError(v)


@PlainSerializer
def _serialize_version(v: Version) -> str:
    return f"{v.major}.{v.minor}"


AnnotatedVersion = Annotated[Version, _validate_version, _serialize_version]


class Config(BaseModel):
    omc: list[AnnotatedVersion]
    py: list[AnnotatedVersion]
