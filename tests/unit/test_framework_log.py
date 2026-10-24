"""Framework output goes to a file while stages run (feature 007, research R1).

The training framework writes part of its output from C++ straight to file descriptor 2, so only a
redirection of the descriptors themselves keeps it off the console. These tests use ``os.write`` on
the descriptors, which is what that C++ output amounts to, and ``capfd`` to see what reached them.
"""

from __future__ import annotations

import os
import sys

import pytest

from caravan.run.framework_log import captured


def test_descriptor_output_lands_in_the_file(tmp_path, capfd) -> None:
    log = tmp_path / "framework.log"
    with captured(log):
        os.write(1, b"to stdout\n")
        os.write(2, b"to stderr\n")
        print("from print")
        print("from print to stderr", file=sys.stderr)
    seen = capfd.readouterr()
    assert seen.out == ""
    assert seen.err == ""
    text = log.read_text(encoding="utf-8")
    for expected in ("to stdout", "to stderr", "from print", "from print to stderr"):
        assert expected in text


def test_output_after_the_block_reaches_the_console(tmp_path, capfd) -> None:
    with captured(tmp_path / "framework.log"):
        os.write(2, b"inside\n")
    os.write(1, b"after out\n")
    print("after err", file=sys.stderr)
    seen = capfd.readouterr()
    assert seen.out == "after out\n"
    assert seen.err == "after err\n"


def test_descriptors_are_restored_when_the_body_raises(tmp_path, capfd) -> None:
    log = tmp_path / "framework.log"
    with pytest.raises(RuntimeError), captured(log):
        os.write(2, b"before the failure\n")
        raise RuntimeError("inside")
    print("visible", file=sys.stderr)
    assert capfd.readouterr().err == "visible\n"
    assert "before the failure" in log.read_text(encoding="utf-8")


def test_an_empty_capture_leaves_no_file(tmp_path) -> None:
    log = tmp_path / "framework.log"
    with captured(log):
        pass
    assert not log.exists()


def test_none_redirects_nothing(capfd) -> None:
    with captured(None):
        os.write(2, b"shown\n")
    assert capfd.readouterr().err == "shown\n"
