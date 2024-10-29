import logging
import sys
from pathlib import Path

import click
from omc4py import open_session

omc4py_logger = logging.getLogger("omc4py")
omc4py_logger.addHandler(logging.StreamHandler())
omc4py_logger.setLevel(logging.DEBUG)


@click.command()
@click.option("--openmodelica-version", required=True)
@click.option("--python-version", required=True)
def main(
    openmodelica_version: str,
    python_version: str,
) -> None:
    s = open_session(version=(1, 24))

    assert sys.version.startswith(f"{python_version}"), "Check Python version"

    version = s.getVersion()
    s.__check__()
    assert version.startswith(f"v{openmodelica_version}"), "Check OpenModelica version"

    installed = s.installPackage("Modelica")
    s.__check__()
    assert installed, "Install Modelica package"

    loaded = s.loadModel("Modelica")
    s.__check__()
    assert loaded, "Load Modelica package"

    result = s.simulate("Modelica.Blocks.Examples.PID_Controller")
    s.__check__()
    assert (
        "The simulation finished successfully." in result.messages
    ), "Check simulation result"
    assert Path(result.resultFile).exists(), "Check simulation output"


if __name__ == "__main__":
    main()
