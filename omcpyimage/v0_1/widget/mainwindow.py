from itertools import chain

from bidict import bidict
from frozendict import frozendict
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMainWindow, QTreeWidgetItem, QWidget

from .. import Version
from ..model import Application, Model, docker, findversion
from ..ui.mainwindow import Ui_MainWindow


class MainWindow(QMainWindow):
    docker_request = Signal(docker.Request)

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
        self.docker_request.connect(model.docker_request)
        model.docker_response.connect(self.update_progress)
        model.findversion_response.connect(self.update_version)

    def update_version(self, response: findversion.Response) -> None:
        images = {
            im | {response.application: v}
            for im in self._topLevelItems
            for v in response.version
        }

        null = Version.model_validate((0,))
        remove = self._topLevelItems.keys() - images
        create = images - self._topLevelItems.keys()

        for callback, image in sorted(
            chain(
                ((self._deleteTopLevelItem, im) for im in remove),
                ((self._newTopLevelItem, im) for im in create),
            ),
            key=lambda fx: tuple(fx[1].get(app, null) for app in Application),
        ):
            callback(image)
            if image in create and image.keys() == set(Application):
                self.docker_request.emit(docker.Request(version=image, push=True))

        return

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

    def _deleteTopLevelItem(self, image: frozendict[Application, Version]) -> None:
        item = self._topLevelItems.pop(image)

        for i in range(self.ui.treeWidget.topLevelItemCount()):
            if self.ui.treeWidget.topLevelItem(i) is item:
                self.ui.treeWidget.takeTopLevelItem(i)

    def columnIndex(self, kind: Application | docker.Stage) -> int:
        _kind: Application | docker.Stage
        header = self.ui.treeWidget.headerItem()
        for i in range(header.columnCount()):
            match header.text(i):
                case "openmodelica":
                    _kind = Application.openmodelica
                case "python":
                    _kind = Application.python
                case "build":
                    _kind = docker.Stage.build
                case "test":
                    _kind = docker.Stage.test
                case "push":
                    _kind = docker.Stage.push

            if _kind == kind:
                return i

        raise NotImplementedError(kind)

    def update_progress(self, response: docker.Response, /) -> None:
        if response.returncode is None:
            text = "running..."
        else:
            text = f"{response.returncode}"

        self._topLevelItems[response.version].setText(
            self.columnIndex(response.stage), text
        )
