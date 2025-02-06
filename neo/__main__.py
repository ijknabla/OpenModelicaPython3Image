from asyncio import run
from functools import wraps

import click

from . import docker_buildx_bake


@click.command()
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def main() -> None:
    await docker_buildx_bake()


if __name__ == "__main__":
    main()
