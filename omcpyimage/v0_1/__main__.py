from __future__ import annotations

from asyncio import gather, run
from collections import defaultdict
from functools import wraps
from importlib.resources import read_binary
from itertools import product
from typing import TYPE_CHECKING

import click

from . import Image, Version

if TYPE_CHECKING:
    from collections.abc import Sequence

    from . import OMVersion, PyVersion


@click.group()
def main() -> None: ...


@main.command()
@click.option("--openmodelica", "--om", multiple=True, type=Version.parse)
@click.option("--python", "--py", multiple=True, type=Version.parse)
@click.option("--check/--no-check", default=False)
@click.option("--push/--no-push", default=False)
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def build(
    openmodelica: Sequence[OMVersion],
    python: Sequence[PyVersion],
    check: bool,
    push: bool,
) -> None:
    image = [
        Image(om=om, py=py)
        for om, py in product(
            sorted(set(openmodelica), key=lambda x: x.as_tuple),
            sorted(set(python), key=lambda x: x.as_tuple),
        )
    ]
    tags = defaultdict[Image, list[str]](lambda: [])
    for im in image:
        tags[im].append(f"ijknabla/openmodelica:v{im.om!s}-python{im.py!s}")

    dockerfile = read_binary(__package__, "Dockerfile")

    await gather(*(im.deploy(dockerfile, tags[im], push=push) for im in image))

    print("=" * 72)
    for _, tt in sorted(tags.items(), key=lambda kv: kv[0].as_tuple):
        for t in tt:
            print(f"- {t}")
    print("=" * 72)


if __name__ == "__main__":
    main()
