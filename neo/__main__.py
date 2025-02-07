import sys
from asyncio import gather, run
from functools import wraps
from itertools import product

import click

from . import OPENMODELICA_URI, PYTHON_URI, DockerBake, Target, categorize_version


@click.command()
@click.option("--indent", type=int)
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def main(*, indent: int | None) -> None:
    openmodelica, python = await gather(
        categorize_version(OPENMODELICA_URI),
        categorize_version(PYTHON_URI),
    )

    targets = [
        Target(
            openmodelica=max(openmodelica_long),
            python=max(python_long),
        )
        for openmodelica_short, openmodelica_long in openmodelica.items() if (1, 20) <= openmodelica_short
        for python_short, python_long in python.items() if (3, 9) <= python_short
    ]

    sys.exit(await DockerBake.from_targets(targets).build(indent=indent))


if __name__ == "__main__":
    main()
