from asyncio import run
from functools import wraps

import click

from . import DockerBake
import sys


@click.command()
@click.option("--indent", type=int)
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def main(*, indent: int | None) -> None:
    sys.exit(await DockerBake.model_validate({}).build(indent=indent))


if __name__ == "__main__":
    main()
