from asyncio import run
from functools import wraps

import click

from . import docker_buildx_bake


@click.command()
@click.option("--indent", type=int)
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def main(*, indent: int | None) -> None:
    await docker_buildx_bake(indent=indent)


if __name__ == "__main__":
    main()
