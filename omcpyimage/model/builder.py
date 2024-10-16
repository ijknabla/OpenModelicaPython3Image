from asyncio import gather
from asyncio.subprocess import PIPE, create_subprocess_exec
from concurrent.futures import Executor
from enum import Enum, auto

from PySide6.QtCore import QObject, Signal

from ..builder import OpenmodelicaPythonImage
from . import run_in_executor


class Builder(QObject):
    start = Signal()
    output = Signal(tuple, bytes)

    class Stage(Enum):
        pull = auto()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        executor: Executor,
        group0: set[OpenmodelicaPythonImage],
        group1: set[OpenmodelicaPythonImage],
        group2: set[OpenmodelicaPythonImage],
    ):
        super().__init__(parent)

        self.executor = executor
        self.group0 = group0
        self.group1 = group1
        self.group2 = group2

        self.start.connect(self._run)

    @property
    def all_group(self) -> set[OpenmodelicaPythonImage]:
        return self.group0 | self.group1 | self.group2

    @run_in_executor
    async def _run(self) -> None:
        await gather(*map(self._pull, self.all_group))

    async def _pull(self, image: OpenmodelicaPythonImage) -> None:
        process = await create_subprocess_exec(*image.pull, stdout=PIPE)
        if process.stdout is None:
            raise RuntimeError
        async for line in process.stdout:
            self.output.emit((Builder.Stage.pull, image), line)
