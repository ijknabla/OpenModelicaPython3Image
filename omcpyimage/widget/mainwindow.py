from PySide6.QtWidgets import QMainWindow, QWidget


class MainWindow(QMainWindow):
    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
