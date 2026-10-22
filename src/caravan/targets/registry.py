"""Loading and listing board descriptions.

A new board is a data file, not a code change (Principle VII). The registry is an instance so a
test can load a directory of deliberately broken board files without touching the shipped ones.
"""

from __future__ import annotations

from functools import lru_cache
from importlib.resources import as_file, files
from pathlib import Path

from caravan.manifest._yaml import read_mapping
from caravan.targets.schema import BoardDescription


class BoardRegistry:
    """Identifier to board description."""

    def __init__(self, boards: dict[str, BoardDescription] | None = None) -> None:
        self._boards: dict[str, BoardDescription] = dict(boards or {})

    def get(self, identifier: str) -> BoardDescription | None:
        return self._boards.get(identifier)

    @property
    def identifiers(self) -> tuple[str, ...]:
        return tuple(sorted(self._boards))

    def __len__(self) -> int:
        return len(self._boards)

    def __iter__(self):
        return iter(self._boards[name] for name in self.identifiers)


def load_directory(directory: Path) -> BoardRegistry:
    """Load every board description in a directory, validating each one."""
    boards: dict[str, BoardDescription] = {}
    for path in sorted(directory.glob("*.yaml")):
        data = read_mapping(path)
        board = BoardDescription.model_validate(data)
        if board.board != path.stem:
            raise ValueError(
                f"{path}: the board identifier {board.board!r} must equal the file name"
            )
        boards[board.board] = board
    return BoardRegistry(boards)


@lru_cache(maxsize=1)
def default_registry() -> BoardRegistry:
    """The boards this build ships."""
    resource = files("caravan.targets").joinpath("boards")
    with as_file(resource) as directory:
        return load_directory(Path(directory))
