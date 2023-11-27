import re
from typing import NamedTuple, Self

from .config import ShortVersion


class LongVersion(NamedTuple):
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, s: str) -> Self:
        if (matched := re.search(r"v?(\d+)\.(\d+)\.(\d+)", s)) is None:
            raise ValueError(s)
        return cls(*map(int, matched.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def as_short(self) -> ShortVersion:
        return ShortVersion(major=self.major, minor=self.minor)
