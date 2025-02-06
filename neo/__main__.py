import sys
from asyncio import run
from functools import wraps

import click

from . import DockerBake


@click.command()
@click.option("--indent", type=int)
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def main(*, indent: int | None) -> None:
    sys.exit(
        await DockerBake.model_validate(
            {
                "group": {"default": {"targets": ["1_24_0-3_12_7"]}},
                "target": {
                    "1_24_0-3_12_7": {
                        "context": ".",
                        "dockerfile": "Dockerfile",
                        "args": {"BASE_IMAGE": "ubuntu:20.04"},
                        "tags": [
                            # "myapp:ubuntu", "myapp:latest"
                        ],
                    },
                },
            }
        ).build(indent=indent)
    )


if __name__ == "__main__":
    main()
