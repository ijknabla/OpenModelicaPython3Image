import pytest

from omcpyimage._types import Level, OMCVersion


@pytest.mark.parametrize("build", range(2))
@pytest.mark.parametrize("stage", [None, *range(2)])
@pytest.mark.parametrize("release", Level)
@pytest.mark.parametrize("micro", range(2))
@pytest.mark.parametrize("minor", range(2))
@pytest.mark.parametrize("major", range(2))
def test_omc_version(
    major: int,
    minor: int,
    micro: int,
    release: Level,
    stage: int | None,
    build: int,
) -> None:
    version = OMCVersion(major=major, minor=minor, micro=micro)
    print(version.omc_repr)
