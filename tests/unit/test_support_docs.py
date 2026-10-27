"""Step blocks are read the way a reader copies them, hyphenated names included (feature 009)."""

from __future__ import annotations

from tests.support_docs import blocks, commands


def test_a_hyphenated_step_is_read(tmp_path) -> None:
    guide = tmp_path / "guide.md"
    guide.write_text(
        "Text.\n\n```bash\n# step: board-copy\ncp a \\\n  b\n# a comment\n```\n\n"
        "```bash\n# step: board-flash\npio run -t upload\n```\n",
        encoding="utf-8",
    )
    assert commands(guide, "board-copy") == ["cp a    b"]
    assert len(blocks(guide, "board-flash")) == 1
    assert blocks(guide, "board") == []
