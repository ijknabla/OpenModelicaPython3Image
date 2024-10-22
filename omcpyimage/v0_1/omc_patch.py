import sys
from argparse import ArgumentParser
from collections.abc import Iterable
from pathlib import Path
from re import search, sub


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("mo", nargs="*")
    args = parser.parse_args()

    for mo in map(Path, args.mo):
        if mo.is_file():
            content0 = mo.read_bytes().splitlines(keepends=True)
            content1 = list(overwrite(content0))
            if content0 != content1:
                mo.write_bytes(b"".join(content1))


def overwrite(content: Iterable[bytes]) -> Iterable[bytes]:
    ROOT_USER_INTERACTIVE = False
    for line in content:
        if search(
            rb"^\s*//\ Don't\ allow\ running\ omc\ as\ root\ due\ to\ security\ risks\.",  # noqa: E501
            line,
        ):
            ROOT_USER_INTERACTIVE |= True
        elif not line or line.isspace():
            ROOT_USER_INTERACTIVE &= False

        if ROOT_USER_INTERACTIVE:
            line = sub(rb"System\.userIsRoot\(\)", rb"/* \g<0> */ false", line)
            sys.stderr.buffer.write(line)
            sys.stderr.buffer.flush()

        yield line


if __name__ == "__main__":
    main()
