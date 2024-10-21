from importlib.resources import as_file, files
from subprocess import run

import click


@click.command()
def main() -> None:
    with as_file(files(__package__)) as directory:
        run(["docker", "build", f"{directory}"], check=True)


if __name__ == "__main__":
    main()
