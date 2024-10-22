from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, StrictInt, model_validator

if TYPE_CHECKING:
    from typing import Any, Self


class Version(BaseModel):
    model_config = ConfigDict(frozen=True)

    major: StrictInt
    minor: StrictInt
    patch: StrictInt

    @classmethod
    def parse(cls, s: str, /, *, strict: bool = True) -> Self:
        pattern = r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
        if strict:
            matched = re.match(rf"^{pattern}$", s)
        else:
            matched = re.search(pattern, s)
        if matched is None:
            raise ValueError(s)
        return cls(
            major=int(matched.group("major")),
            minor=int(matched.group("minor")),
            patch=int(matched.group("patch")),
        )

    @property
    def tuple(self) -> tuple[int, int, int]:
        return self.major, self.minor, self.patch

    def __str__(self) -> str:
        return ".".join(map(str, self.tuple))

    @model_validator(mode="before")  # type: ignore [arg-type]
    @classmethod
    def _model_validate(cls, obj: Any, /) -> Any:
        if isinstance(obj, str):
            return cls.parse(obj, strict=True).model_dump()
        return obj
