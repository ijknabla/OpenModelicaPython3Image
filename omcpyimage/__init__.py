from __future__ import annotations

from typing import Any

__version__ = "0.0.1a0.dev0"


class NoLock:
    async def __aenter__(self) -> None:
        return

    async def __aexit__(self, *exc_info: Any) -> None:
        return
