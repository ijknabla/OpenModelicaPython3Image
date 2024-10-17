from asyncio import gather
from asyncio.subprocess import PIPE, create_subprocess_exec
from collections.abc import Sequence
from concurrent.futures import Executor
from enum import Enum, auto
from itertools import chain
from typing import NamedTuple

from PySide6.QtCore import QObject, Signal

from ..types import LongVersion
from . import run_in_executor


class Stage(Enum):
    pull = auto()


class OpenmodelicaPythonImage(NamedTuple):
    base: str
    ubuntu: str
    openmodelica: str
    python: LongVersion

    @property
    def openmodelica_version(self) -> LongVersion:
        return LongVersion.parse(self.openmodelica)

    @property
    def tag(self) -> str:
        openmodelica = LongVersion.parse(self.openmodelica)
        return f"v{openmodelica}-python{self.python.as_short()}"

    @property
    def image(self) -> str:
        return f"{self.base}:{self.tag}"

    def command(self, stage: Stage) -> tuple[str, ...]:
        if stage is Stage.pull:
            return "docker", "pull", self.image

    # def push(self) -> Future[None]:
    #     return _run("docker", "push", self.image)

    # def build(self) -> Future[None]:
    #     dockerfile = Path(resource_filename(__name__, "Dockerfile")).resolve()
    #     return _run(
    #         "docker",
    #         "build",
    #         f"{dockerfile.parent}",
    #         f"--tag={self.image}",
    #         f"--build-arg=BUILD_IMAGE={self.ubuntu}",
    #         f"--build-arg=OPENMODELICA_IMAGE={self.openmodelica}",
    #         f"--build-arg=PYTHON_VERSION={self.python}",
    #     )


class Builder(QObject):
    start = Signal()
    process_start = Signal(OpenmodelicaPythonImage, Stage)
    process_output = Signal(OpenmodelicaPythonImage, Stage, bytes)
    process_returncode = Signal(OpenmodelicaPythonImage, Stage, int)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        executor: Executor,
        groups: Sequence[set[OpenmodelicaPythonImage]],
    ):
        super().__init__(parent)

        self.executor = executor
        self.groups = groups

        self.start.connect(self._run)

    @run_in_executor
    async def _run(self) -> None:
        await gather(
            *(
                self._execute(image, Stage.pull)
                for image in chain.from_iterable(self.groups)
            )
        )

    async def _execute(self, image: OpenmodelicaPythonImage, stage: Stage) -> None:
        process = await create_subprocess_exec(*image.command(stage), stdout=PIPE)
        self.process_start.emit(image, stage)
        if process.stdout is None:
            raise RuntimeError
        async for line in process.stdout:
            self.process_output.emit(image, stage, line)
        self.process_returncode.emit(image, stage, process.returncode)
