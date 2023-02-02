from contextlib import ExitStack
from itertools import product
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory

distro_names = ["bullseye"]
python_versions = ["3.10"]
modelica_versions = ["1.20.0"]


def main():
    for distro_name, python_version in product(distro_names, python_versions):
        dockerfile = f"""
FROM python:{python_version}-{distro_name}
        """

        with ExitStack() as stack:
            directory = Path(stack.enter_context(TemporaryDirectory()))
            (directory / "Dockerfile").write_text(dockerfile)
            run(["docker", "build", "."], cwd=directory)


if __name__ == "__main__":
    main()
