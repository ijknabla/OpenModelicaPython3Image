from __future__ import annotations

import re
from asyncio import create_subprocess_exec
from collections.abc import AsyncIterator
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath
from subprocess import PIPE
from urllib.parse import urlparse

from pydantic import BaseModel

from .. import Version
from .constant import Application


class Request(BaseModel):
    application: Application

    async def reply(self) -> AsyncIterator[Response]:
        async for tag in self.iter_tags():
            match re.match(r"^v(?P<version>\d+\.\d+\.\d+)$", tag):
                case None:
                    continue
                case matched:
                    version = Version.model_validate(matched.group("version"))

            yield Response(application=self.application, version=version)
        yield Response(application=self.application, version=None)

    async def iter_tags(self) -> AsyncIterator[str]:
        git_clone = await create_subprocess_exec(
            "git", "clone", "--bare", self.uri, self.local.__fspath__()
        )
        await git_clone.wait()

        git_fetch = await create_subprocess_exec(
            "git", "-C", self.local.__fspath__(), "fetch"
        )
        await git_fetch.wait()

        git_tag = await create_subprocess_exec(
            "git", "-C", self.local.__fspath__(), "tag", "--list", stdout=PIPE
        )
        if git_tag.stdout is None:
            raise RuntimeError

        async for line in git_tag.stdout:
            tag = line.decode("utf-8").strip()
            if tag:
                yield tag

    @property
    def uri(self) -> str:
        return {
            Application.openmodelica: "https://github.com/OpenModelica/OpenModelica.git",
            Application.python: "https://github.com/python/cpython.git",
        }[self.application]

    @property
    def local(self) -> Path:
        name = PurePosixPath(urlparse(self.uri).path).name
        with as_file(files(__package__).joinpath(f".cache/git/{name}")) as local:
            return local


class Response(BaseModel):
    application: Application
    version: Version | None
