from contextlib import ExitStack

import pytest

from omcpyimage._apis import parse_omc_version, parse_version
from omcpyimage._types import OMCVersion, Release, Version


@pytest.mark.parametrize("minor", range(2))
@pytest.mark.parametrize("major", range(2))
def test_version(
    major: int,
    minor: int,
) -> None:
    version = Version(major=major, minor=minor)

    assert version == parse_version(f"{version!s}")


@pytest.mark.parametrize("build", range(2))
@pytest.mark.parametrize("stage", [None, *range(2)])
@pytest.mark.parametrize("release", Release)
@pytest.mark.parametrize("micro", range(2))
@pytest.mark.parametrize("minor", range(2))
@pytest.mark.parametrize("major", range(2))
def test_omc_version(
    major: int,
    minor: int,
    micro: int,
    release: Release,
    stage: int | None,
    build: int,
) -> None:
    version: OMCVersion | None = None
    with ExitStack() as stack:
        if not (release is Release.final) == (stage is None):
            stack.enter_context(pytest.raises(ValueError))
        version = OMCVersion(
            major=major,
            minor=minor,
            micro=micro,
            release=release,
            stage=stage,
            build=build,
        )
    if version is None:
        return

    assert version == parse_omc_version(f"{version}")
