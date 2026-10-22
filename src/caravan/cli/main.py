"""The command line: the contract for people and for continuous integration.

Exit codes distinguish a rule saying no from a defect in the tool (FR-004):

* 0 — the manifest is valid; any requested artifact was written
* 1 — the manifest is invalid, or its declared schema version is unknown
* 2 — usage error: unknown option, missing argument, unreadable path
* 3 — internal failure of the tool itself, reported as one, with a trace
* 4 — the environment is incomplete: a part that installs separately is not there

Code 4 arrived with feature 002 and exists because a missing training framework is neither a
broken rule nor a defect in the tool. A continuous integration job can act on each of the five
differently, which it could not if a missing install arrived as code 1.

There is no option that skips, forces or silences a check (FR-005, Principle V).
"""

from __future__ import annotations

import argparse
import sys
import traceback
from collections.abc import Sequence

from caravan import __version__

EXIT_OK = 0
EXIT_RULE = 1
EXIT_USAGE = 2
EXIT_INTERNAL = 3
EXIT_ENVIRONMENT = 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="caravan",
        description="Declarative pipeline for small models on microcontrollers.",
    )
    parser.add_argument("--version", action="version", version=f"caravan-ml {__version__}")
    subcommands = parser.add_subparsers(dest="command", metavar="<command>")

    def add_report_options(sub: argparse.ArgumentParser) -> None:
        sub.add_argument(
            "--runs-dir",
            default="runs",
            metavar="<path>",
            help="where the run directory is created (default: runs)",
        )
        sub.add_argument(
            "--json", action="store_true", help="findings on standard output as one JSON document"
        )
        sub.add_argument(
            "-q", "--quiet", action="store_true", help="suppress the human summary; exit code only"
        )

    validate = subcommands.add_parser("validate", help="check one manifest")
    validate.add_argument("manifest", metavar="<manifest>")
    validate.add_argument(
        "--no-report", action="store_true", help="check only, write nothing at all"
    )
    add_report_options(validate)

    render = subcommands.add_parser(
        "render", help="write the fully resolved manifest and the run report"
    )
    render.add_argument("manifest", metavar="<manifest>")
    render.add_argument(
        "--stdout",
        action="store_true",
        help="write the resolved manifest to standard output instead of a run directory",
    )
    add_report_options(render)

    def add_stage_options(sub: argparse.ArgumentParser) -> None:
        """What the two stage verbs share. Nothing here can skip a rule — only the cache."""
        sub.add_argument("manifest", metavar="<manifest>")
        sub.add_argument(
            "--cache-dir",
            default=".caravan/cache",
            metavar="<path>",
            help="where stage results are stored (default: .caravan/cache)",
        )
        sub.add_argument(
            "--fresh",
            action="store_true",
            help="ignore any cached result and produce it again; recorded in the report",
        )
        add_report_options(sub)

    build = subcommands.add_parser(
        "build", help="construct the model the manifest describes, and report its shape"
    )
    add_stage_options(build)

    train = subcommands.add_parser(
        "train", help="train the model on the dataset the manifest names"
    )
    add_stage_options(train)

    subcommands.add_parser("templates", help="list the registered template identifiers")
    subcommands.add_parser("boards", help="list the known board identifiers")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help(sys.stderr)
        return EXIT_USAGE

    # Imported here, not at module import time, so that `caravan --version` and the usage path
    # stay as light as the package itself.
    from caravan.cli import build as build_command
    from caravan.cli import listing
    from caravan.cli import render as render_command
    from caravan.cli import train as train_command
    from caravan.cli import validate as validate_command

    handlers = {
        "validate": validate_command.run,
        "render": render_command.run,
        "build": build_command.run,
        "train": train_command.run,
        "templates": listing.run_templates,
        "boards": listing.run_boards,
    }
    try:
        return handlers[args.command](args)
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        print("caravan: interrupted", file=sys.stderr)
        return EXIT_USAGE
    except Exception:
        traceback.print_exc()
        print(
            "caravan: this is a defect in caravan itself, not a problem with your manifest",
            file=sys.stderr,
        )
        return EXIT_INTERNAL


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
