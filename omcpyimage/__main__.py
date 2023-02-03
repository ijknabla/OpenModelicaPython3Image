from itertools import product

from . import get_openmodelica_vs_debian, get_python_vs_debian, run_coroutine
from ._types import Debian, OpenModelica, Python


@run_coroutine
async def main() -> None:
    openmodelica_vs_debian = await get_openmodelica_vs_debian()
    for (i, openmodelica), (j, debian) in product(
        enumerate(OpenModelica), enumerate(Debian)
    ):
        patch, build = openmodelica_vs_debian[i, j]
        if 0 <= patch and 0 <= build:
            print(f"{openmodelica}-{debian}", patch, build)

    python_vs_debian = await get_python_vs_debian()
    for python, row in zip(Python, python_vs_debian):
        for debian, value in zip(Debian, row):
            print(f"{python}-{debian}", value)


if __name__ == "__main__":
    main()
