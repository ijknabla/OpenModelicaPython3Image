from collections.abc import Iterator

from bidict import bidict
from frozendict import frozendict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QWidget

from .. import Version
from ..model import Application, Model, findversion
from ..ui.mainwindow import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(
        self, parent: QWidget | None = None, flags: Qt.WindowType | None = None
    ) -> None:
        super().__init__(parent, flags if flags is not None else Qt.WindowType(0))

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self._topLevelItems = bidict[
            frozendict[Application, Version], QTreeWidgetItem
        ]()
        self._newTopLevelItem(frozendict[Application, Version]())

    def setModel(self, model: Model) -> None:
        model.findversion_response.connect(self.update_version)

    def update_version(self, response: findversion.Response) -> None:
        oposite = {
            Application.openmodelica: Application.python,
            Application.python: Application.openmodelica,
        }[response.application]

        def _iter_items() -> Iterator[QTreeWidgetItem]:
            for i in range(self.ui.treeWidget.topLevelItemCount()):
                item = self.ui.treeWidget.topLevelItem(i)
                oposite_text = item.text(self.columnIndex(oposite))

                for version in response.version:
                    new_item = QTreeWidgetItem()
                    new_item.setText(
                        self.columnIndex(response.application), f"v{version}"
                    )
                    new_item.setText(self.columnIndex(oposite), oposite_text)

                    yield new_item

        items = list(_iter_items())
        self.ui.treeWidget.clear()
        self.ui.treeWidget.addTopLevelItems(items)

    def _newTopLevelItem(
        self, image: frozendict[Application, Version]
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem()

        for app in Application:
            version = image.get(app)
            item.setText(
                self.columnIndex(app), f"v{version}" if version is not None else "-"
            )

        self.ui.treeWidget.addTopLevelItem(item)
        self._topLevelItems[image] = item

        return item

    def columnIndex(self, kind: Application) -> int:
        header = self.ui.treeWidget.headerItem()
        for i in range(header.columnCount()):
            match header.text(i):
                case "openmodelica":
                    _kind = Application.openmodelica
                case "python":
                    _kind = Application.python

            if _kind == kind:
                return i

        raise NotImplementedError(kind)
