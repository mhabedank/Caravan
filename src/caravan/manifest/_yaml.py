"""The only module in the package that imports a YAML library.

Why it is isolated: the YAML dependency is the one Principle XII already forced a choice on
(``ruamel.yaml`` rather than ``pyyaml``, because ``pyyaml`` publishes no wheel for the current
stable Python). Keeping every import of it behind one module is what makes that choice cheap to
revisit — see ``specs/001-manifest-schema/research.md``, R2.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError


class DocumentError(Exception):
    """A file could not be read as a manifest or board document at all.

    This is not a rule violation: nothing was validated, because nothing could be parsed. The
    command line reports it with the same shape as a finding but without a rule identifier.
    """

    def __init__(self, path: Path, problem: str, location: str | None = None) -> None:
        self.path = path
        self.problem = problem
        self.location = location
        super().__init__(f"{path}: {problem}" + (f" ({location})" if location else ""))


def _reader() -> YAML:
    yaml = YAML(typ="safe")
    yaml.pure = True
    return yaml


def read_mapping(path: Path) -> dict[str, Any]:
    """Read one YAML document and return it as a mapping.

    Raises ``DocumentError`` for a missing or unreadable file, for invalid YAML, for an empty
    document and for a document that is not a mapping — each reported as what it is, with the
    position when the parser gives one.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise DocumentError(path, "no such file") from exc
    except IsADirectoryError as exc:
        raise DocumentError(path, "this is a directory, not a file") from exc
    except UnicodeDecodeError as exc:
        raise DocumentError(path, "the file is not valid UTF-8 text") from exc
    except OSError as exc:
        raise DocumentError(path, f"the file could not be read: {exc.strerror}") from exc

    try:
        data = _reader().load(text)
    except YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        location = f"line {mark.line + 1}, column {mark.column + 1}" if mark is not None else None
        problem = getattr(exc, "problem", None) or "the file is not valid YAML"
        raise DocumentError(path, f"the file is not valid YAML: {problem}", location) from exc

    if data is None:
        raise DocumentError(path, "the file is empty")
    if not isinstance(data, dict):
        raise DocumentError(
            path, f"the document is a {type(data).__name__}, and a manifest must be a mapping"
        )
    return data


def dump_mapping(data: dict[str, Any]) -> str:
    """Serialise a mapping deterministically, preserving the order it was built in.

    Key order is the schema's, never the input file's, so that two runs of the same input are
    byte-comparable (research R9). Sorting is switched off for the same reason: the order has to
    come from the schema, not from the alphabet.
    """
    yaml = YAML(typ="safe")
    yaml.pure = True
    yaml.default_flow_style = False
    yaml.representer.sort_base_mapping_type_on_output = False
    yaml.width = 100
    stream = io.StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()
