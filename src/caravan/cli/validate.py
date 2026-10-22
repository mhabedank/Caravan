"""``caravan validate`` — is this manifest sound?"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from caravan.cli.main import EXIT_OK, EXIT_RULE, EXIT_USAGE
from caravan.manifest._yaml import DocumentError
from caravan.manifest.errors import render_document_error, render_finding
from caravan.manifest.load import LoadOutcome, load_manifest
from caravan.run.paths import create_run_directory, file_digest
from caravan.run.report import OUTCOME_INVALID, OUTCOME_VALID, Report, write_report


def json_document(manifest_name: str, outcome: LoadOutcome) -> str:
    return (
        json.dumps(
            {
                "manifest": manifest_name,
                "outcome": OUTCOME_VALID if outcome.is_valid else OUTCOME_INVALID,
                "schema_version_declared": outcome.declared_version,
                "schema_version_effective": outcome.effective_version,
                "findings": [finding.as_dict() for finding in outcome.findings],
                "unresolved": [item.as_dict() for item in outcome.unresolved],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )


def report_for(command: str, path: Path, outcome: LoadOutcome, **extra: object) -> Report:
    manifest = outcome.manifest
    return Report(
        command=command,
        manifest_path=str(path),
        manifest_sha256=file_digest(path),
        outcome=OUTCOME_VALID if outcome.is_valid else OUTCOME_INVALID,
        schema_version_declared=outcome.declared_version,
        schema_version_effective=outcome.effective_version,
        migrations_applied=outcome.migrations_applied,
        dataset=manifest.dataset.source if manifest else None,
        template=manifest.model.template if manifest else None,
        gates=tuple(outcome.gates),
        findings=tuple(outcome.findings),
        unresolved=tuple(outcome.unresolved),
        seed=manifest.train.seed if manifest else None,
        **extra,  # type: ignore[arg-type]
    )


def report_outcome(args: argparse.Namespace, path: Path, outcome: LoadOutcome) -> int:
    """Print findings, write the report when asked, and return the exit code."""
    name = path.name
    if args.json:
        sys.stdout.write(json_document(name, outcome))
    elif not args.quiet:
        for finding in outcome.findings:
            print(render_finding(name, finding), file=sys.stderr)
        if outcome.is_valid:
            print(f"{name}: valid", file=sys.stderr)
        else:
            count = len(outcome.findings)
            print(f"{name}: invalid — {count} finding{'s' if count != 1 else ''}", file=sys.stderr)

    if not getattr(args, "no_report", False):
        run_dir = create_run_directory(Path(args.runs_dir), file_digest(path))
        written = write_report(run_dir, report_for("validate", path, outcome))
        if not args.quiet and not args.json:
            print(f"{name}: report written to {written}", file=sys.stderr)

    return EXIT_OK if outcome.is_valid else EXIT_RULE


def run(args: argparse.Namespace) -> int:
    path = Path(args.manifest)
    try:
        outcome = load_manifest(path)
    except DocumentError as exc:
        print(render_document_error(exc.path.name, exc.problem, exc.location), file=sys.stderr)
        return EXIT_USAGE
    return report_outcome(args, path, outcome)
