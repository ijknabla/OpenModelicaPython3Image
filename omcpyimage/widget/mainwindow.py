from collections import defaultdict
from collections.abc import Iterable, Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QWidget

from ..builder import OpenmodelicaPythonImage
from ..types import LongVersion
from ..ui.mainwindow import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(
        self,
        parent: QWidget | None = None,
        flags: Qt.WindowType | None = None,
    ) -> None:
        super().__init__(parent, flags if flags is not None else Qt.WindowType(0))

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)  # type: ignore [no-untyped-call]

        self.ui.treeWidget.itemClicked.connect(print)

    def setImages(self, images: Iterable[OpenmodelicaPythonImage]) -> None:
        categories: Mapping[str, list[OpenmodelicaPythonImage]] = defaultdict[
            str, list[OpenmodelicaPythonImage]
        ](lambda: [])

        for image in sorted(images, key=lambda x: x.python):
            categories[image.openmodelica].append(image)

        categories = dict(
            (k, sorted(v))
            for k, v in sorted(
                categories.items(), key=lambda x: LongVersion.parse(x[0])
            )
        )

        for k, vv in categories.items():
            item0 = QTreeWidgetItem(self.ui.treeWidget)
            item0.setText(0, f"{LongVersion.parse(k)}")

            for v in vv:
                item1 = QTreeWidgetItem(item0)
                item1.setText(0, f"{LongVersion.parse(k)}")
                item1.setText(1, f"{v.python}")
