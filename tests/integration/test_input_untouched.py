"""Quickstart scenario 4: the author's file is never modified.

This is the scenario that matters for an archived manifest. Reading one — including migrating it
— must not rewrite it.
"""

from __future__ import annotations

import hashlib
import shutil

from caravan.cli.main import main
from tests.support import PILOT


def digest(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_neither_command_touches_the_manifest(tmp_path, capsys) -> None:
    manifest = tmp_path / "picket-mlp.yaml"
    shutil.copy(PILOT, manifest)
    before = digest(manifest)
    mtime_before = manifest.stat().st_mtime_ns

    main(["validate", str(manifest), "--runs-dir", str(tmp_path / "runs")])
    main(["render", str(manifest), "--runs-dir", str(tmp_path / "runs")])
    main(["render", str(manifest), "--stdout"])
    capsys.readouterr()

    assert digest(manifest) == before
    assert manifest.stat().st_mtime_ns == mtime_before


def test_nothing_is_written_beside_the_manifest(tmp_path, capsys) -> None:
    manifest = tmp_path / "picket-mlp.yaml"
    shutil.copy(PILOT, manifest)
    main(["validate", str(manifest), "--runs-dir", str(tmp_path / "runs")])
    capsys.readouterr()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["picket-mlp.yaml", "runs"]
