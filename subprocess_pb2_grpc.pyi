
from __future__ import annotations
import collections as _collections
import typing as _typing
import grpc
_ChannelType = _typing.TypeVar('_ChannelType', grpc.Channel, grpc.aio.Channel)
_ServerType = _typing.TypeVar('_ServerType', grpc.Server, grpc.aio.Server)

class SubprocessStub(_typing.Generic[_ChannelType]):

    def __init__(self, channel: _ChannelType) -> None:
        ...

class SubprocessServicer(_typing.Generic[_ServerType]):
    pass

def add_SubprocessServicer_to_server(servicer: SubprocessServicer[_ServerType], server: _ServerType) -> None:
    ...
