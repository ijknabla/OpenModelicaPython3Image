from asyncio import gather

from . import get_openmodelica_vs_distro, get_python_vs_debian, run_coroutine
from ._types import Debian, DistroName, Python


@run_coroutine
async def main() -> None:
    openmodelica_vs_distro = await get_openmodelica_vs_distro(
        map(DistroName, ["stretch", "buster", "bullseye"])
    )

    for (distro_name, _), omc_version in openmodelica_vs_distro.items():
        print(f"{distro_name=!s}, {omc_version=!s}")

    return
    openmodelica_vs_distro, python_vs_debian = await gather(
        get_openmodelica_vs_distro([DistroName("bullseye")]),
        get_python_vs_debian(),
    )

    for python, row in zip(Python, python_vs_debian):
        for debian, value in zip(Debian, row):
            print(f"{python}-{debian}", value)


if __name__ == "__main__":
    main()
