import sys
from asyncio import run
from functools import wraps
from itertools import product

import click

from . import DockerBake, Target


@click.command()
@click.option("--indent", type=int)
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def main(*, indent: int | None) -> None:
    targets = [
        Target(
            openmodelica=openmodelica,
            python=python,
        )
        for openmodelica, python in product([(1, 24, 0)], [(3, 12, 7)])
    ]

    sys.exit(await DockerBake.from_targets(targets).build(indent=indent))


if __name__ == "__main__":
    main()
