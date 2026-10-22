"""``caravan templates`` and ``caravan boards``.

Every rejection of an unknown identifier promises a list of the known ones. These commands are
how a user asks for that list without having to trigger an error first, and a test asserts they
come from the same registries the messages cite.
"""

from __future__ import annotations

import argparse

from caravan.cli.main import EXIT_OK
from caravan.targets.registry import default_registry as default_boards
from caravan.templates.registry import default_registry as default_templates


def run_templates(_args: argparse.Namespace) -> int:
    for spec in default_templates():
        print(f"{spec.identifier}\t{spec.summary}")
    return EXIT_OK


def run_boards(_args: argparse.Namespace) -> int:
    for board in default_boards():
        emulator = board.emulator.platform if board.emulator else "no emulator platform"
        print(
            f"{board.board}\t{board.core}, {board.clock_mhz:g} MHz, "
            f"{board.ram_kb:g} KB RAM, {board.flash_kb:g} KB flash, {board.accel}, {emulator}"
        )
    return EXIT_OK
