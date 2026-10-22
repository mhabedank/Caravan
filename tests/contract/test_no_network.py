"""No command in this feature opens a network connection (Principle VIII).

This is also the precondition for Principle VI's promise that publication cannot happen before
compliance is checked: a stage that cannot reach the network cannot upload anything.
"""

from __future__ import annotations

import socket

import pytest

from caravan.cli.main import EXIT_OK, EXIT_RULE, main
from tests.support import INVALID, PILOT


@pytest.fixture
def no_network(monkeypatch) -> None:
    def refuse(*_args, **_kwargs):
        raise AssertionError("a command tried to open a socket")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)


def test_validate_needs_no_network(no_network, tmp_path, capsys) -> None:
    assert main(["validate", str(PILOT), "--runs-dir", str(tmp_path)]) == EXIT_OK


def test_render_needs_no_network(no_network, tmp_path, capsys) -> None:
    assert main(["render", str(PILOT), "--runs-dir", str(tmp_path)]) == EXIT_OK


def test_rejection_needs_no_network(no_network, tmp_path, capsys) -> None:
    manifest = INVALID / "cf-8-benchmark-only-publish.yaml"
    assert main(["validate", str(manifest), "--runs-dir", str(tmp_path)]) == EXIT_RULE


def test_the_listings_need_no_network(no_network, capsys) -> None:
    assert main(["templates"]) == EXIT_OK
    assert main(["boards"]) == EXIT_OK
