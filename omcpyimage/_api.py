from contextlib import suppress

from ._types import LongVersion, Version


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
