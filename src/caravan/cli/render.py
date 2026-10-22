"""``caravan render`` — what will the pipeline actually use?"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from caravan.cli.main import EXIT_OK, EXIT_RULE, EXIT_USAGE
from caravan.cli.validate import json_document, report_for
from caravan.manifest._yaml import DocumentError
from caravan.manifest.errors import render_document_error, render_finding
from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import render as render_manifest
from caravan.run.paths import RESOLVED_MANIFEST_NAME, create_run_directory, file_digest
from caravan.run.report import write_report


def run(args: argparse.Namespace) -> int:
    path = Path(args.manifest)
    try:
        outcome = load_manifest(path)
    except DocumentError as exc:
        print(render_document_error(exc.path.name, exc.problem, exc.location), file=sys.stderr)
        return EXIT_USAGE

    name = path.name
    if not outcome.is_valid:
        if args.json:
            sys.stdout.write(json_document(name, outcome))
        elif not args.quiet:
            for finding in outcome.findings:
                print(render_finding(name, finding), file=sys.stderr)
            print(f"{name}: invalid — nothing was written", file=sys.stderr)
        if not args.stdout:
            run_dir = create_run_directory(Path(args.runs_dir), file_digest(path))
            write_report(run_dir, report_for("render", path, outcome))
        return EXIT_RULE

    assert outcome.manifest is not None
    resolved = render_manifest(outcome.manifest)

    if args.stdout:
        # Nothing is written to disk and no run directory is created, so the command stays usable
        # in a pipeline. The text is byte-identical to the file form.
        sys.stdout.write(resolved)
        return EXIT_OK

    run_dir = create_run_directory(Path(args.runs_dir), file_digest(path))
    (run_dir / RESOLVED_MANIFEST_NAME).write_text(resolved, encoding="utf-8")
    report = report_for(
        "render", path, outcome, artifacts={"resolved_manifest": RESOLVED_MANIFEST_NAME}
    )
    written = write_report(run_dir, report)
    if args.json:
        sys.stdout.write(json_document(name, outcome))
    elif not args.quiet:
        print(f"{name}: valid", file=sys.stderr)
        print(f"{name}: resolved manifest and report written to {run_dir}", file=sys.stderr)
    _ = written
    return EXIT_OK
