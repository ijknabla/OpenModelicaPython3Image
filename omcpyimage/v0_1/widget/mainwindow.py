from collections.abc import Iterator
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack, contextmanager
from typing import Self

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtWidgets import QMainWindow, QWidget

from ..model import Model
from ..ui.mainwindow import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(
        self, parent: QWidget | None = None, flags: Qt.WindowType | None = None
    ) -> None:
        super().__init__(parent, flags if flags is not None else Qt.WindowType(0))

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

    @classmethod
    @contextmanager
    def open(cls) -> Iterator[Self]:
        with ExitStack() as stack:
            self = cls()

            pool = QThreadPool(self)
            stack.callback(pool.waitForDone, -1)

            executor = stack.enter_context(ProcessPoolExecutor())
            stack.enter_context(Model.open(self, executor=executor, pool=pool))

            yield self
