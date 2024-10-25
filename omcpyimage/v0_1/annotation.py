from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

import PySide6.QtCore
from PySide6.QtCore import QMetaObject, QObject, Qt

_T = TypeVar("_T")


if TYPE_CHECKING:

    class _MetaSignal:
        def __getitem__(self, type_hint: type[_T], /) -> SignalInstance[_T]: ...

    class Signal(Generic[_T]):
        def __init__(self, type: type[_T]) -> None: ...

        def __get__(
            self, obj: QObject, objtype: type[QObject] | None = None, /
        ) -> SignalInstance[_T]: ...

    class SignalInstance(Generic[_T]):
        def connect(
            self, slot: Callable[[_T], Any], type: Qt.ConnectionType = ...
        ) -> QMetaObject.Connection: ...
        def disconnect(self, slot: Callable[[_T], Any] | None = ...) -> bool: ...
        def emit(self, arg: _T, /) -> None: ...

else:
    Signal = PySide6.QtCore.Signal

    class SignalInstance:
        def __class_getitem__(self, _, /):
            return PySide6.QtCore.SignalInstance
