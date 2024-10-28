from __future__ import annotations

from collections.abc import AsyncIterator

from frozendict import frozendict
from pydantic import BaseModel, ConfigDict

from .. import Version
from .constant import Application


class Request(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    version: frozendict[Application, Version]

    async def reply(self) -> AsyncIterator[Response]:
        yield Response()


class Response(BaseModel): ...
