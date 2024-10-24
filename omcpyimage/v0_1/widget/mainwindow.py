from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget

from ..ui.mainwindow import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(
        self, parent: QWidget | None = None, flags: Qt.WindowType | None = None
    ) -> None:
        super().__init__(parent, flags if flags is not None else Qt.WindowType(0))

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
