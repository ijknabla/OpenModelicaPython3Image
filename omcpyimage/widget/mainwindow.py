from collections import defaultdict
from collections.abc import Iterable

from bidict import bidict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QWidget

from ..config import Config
from ..model.builder import OpenmodelicaPythonImage, Stage
from ..types import LongVersion
from ..ui.mainwindow import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(
        self,
        parent: QWidget | None = None,
        flags: Qt.WindowType | None = None,
        *,
        config: Config,
    ) -> None:
        super().__init__(parent, flags if flags is not None else Qt.WindowType(0))

        self.config = config

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)  # type: ignore [no-untyped-call]

        self.treeWidgetItems = bidict[OpenmodelicaPythonImage, QTreeWidgetItem]()

        self.ui.treeWidget.itemClicked.connect(self._treeWidgetItemClicked)

    def setImages(self, images: Iterable[OpenmodelicaPythonImage]) -> None:
        categories = defaultdict[LongVersion, list[OpenmodelicaPythonImage]](lambda: [])

        for image in sorted(images, key=lambda x: (x.openmodelica_version, x.python)):
            categories[image.openmodelica_version].append(image)

        for k, vv in categories.items():
            item0 = QTreeWidgetItem(self.ui.treeWidget)
            item0.setText(0, f"{k}")

            for v in vv:
                item1 = QTreeWidgetItem(item0)
                item1.setText(0, f"{k}")
                item1.setText(1, f"{v.python}")

                self.treeWidgetItems[v] = item1

    def _treeWidgetItemClicked(self, item: QTreeWidgetItem, col: int) -> None:
        if item in self.treeWidgetItems.values():
            print(self.treeWidgetItems.inv[item])

    def update_process_status(
        self,
        image: OpenmodelicaPythonImage,
        stage: Stage,
        returncode: int | None = None,
    ) -> None:
        column = {Stage.pull: 2, Stage.build: 3, Stage.push: 4}[stage]
        text = f"{returncode}" if returncode is not None else "running..."

        self.treeWidgetItems[image].setText(column, text)
