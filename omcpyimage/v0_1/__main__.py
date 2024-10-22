import re
import sys
from asyncio import run
from asyncio.subprocess import PIPE, create_subprocess_exec
from functools import wraps
from importlib.resources import as_file, files

import click


@click.command()
@(lambda f: wraps(f)(lambda *args, **kwargs: run(f(*args, **kwargs))))
async def main() -> None:
    writing_image = re.compile(r"writing image sha256:(?P<sha256>[0-9a-f]{64}) done")

    images = list[str]()

    with as_file(files(__package__)) as directory:
        docker_build = await create_subprocess_exec(
            "docker", "build", f"{directory}", stderr=PIPE
        )
        if docker_build.stderr is None:
            raise RuntimeError
        async for _line in docker_build.stderr:
            line = _line.decode("utf-8")
            print(line, end="", file=sys.stderr)
            if matched := writing_image.search(line):
                images.append(matched.group("sha256"))

    print("=" * 79)
    for image in images:
        print(f"docker run -it {image}")
    print("=" * 79)

    sys.exit(docker_build.returncode)


if __name__ == "__main__":
    main()
