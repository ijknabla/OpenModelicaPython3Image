from . import get_python_vs_debian, run_coroutine
from ._types import Debian, Python


@run_coroutine
async def main() -> None:
    if __debug__:
        python_vs_debian = await get_python_vs_debian()
        for python, row in zip(Python, python_vs_debian):
            for debian, value in zip(Debian, row):
                print(f"{python}-{debian}", value)


if __name__ == "__main__":
    main()
