"""What ``build`` and ``train`` share: load, resolve, run stages, report.

Both verbs are the same sequence with a different last stage, so the sequence lives here once. The
order of the steps is part of the contract and not an implementation detail:

1. the manifest is checked first, so a broken manifest never creates a run directory;
2. the environment is checked next, so a missing extra never creates one either — the user asked
   for something this installation cannot do, and leaving an empty run directory behind would be
   a worse answer than none;
3. the run directory is created *before* the dataset is resolved, so a dataset that disagrees with
   the manifest is recorded in a report rather than only printed.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from caravan.cli.main import EXIT_ENVIRONMENT, EXIT_OK, EXIT_RULE, EXIT_USAGE
from caravan.cli.validate import json_document, report_for
from caravan.env import EnvironmentIncomplete, missing_extra_message, training_framework_available
from caravan.manifest._yaml import DocumentError
from caravan.manifest.errors import (
    Finding,
    Gate,
    RunRuleFailure,
    render_document_error,
    render_finding,
)
from caravan.manifest.load import load_manifest
from caravan.manifest.resolve import render as render_manifest
from caravan.manifest.resolve import resolve
from caravan.run.paths import RESOLVED_MANIFEST_NAME, create_run_directory, file_digest
from caravan.run.report import (
    OUTCOME_ERROR,
    ConfusionMatrix,
    QualityMetric,
    Report,
    StageOutcome,
    write_report,
)
from caravan.stages import cache as cache_module
from caravan.stages.base import StageContext, StageSpec, run_stage

#: The files a stage writes its measurements into, and the ones the report is built from — so a
#: reused result reports the same numbers as the run that produced it. A stage that fails a gate
#: writes its record straight into the run directory, so the same read serves both paths.
METRICS_NAME = "metrics.json"
QUANTIZATION_NAME = "quantization.json"

#: Printed after a successful run: the manifest's name, the run directory and what the stages
#: measured. The name comes first in every line Caravan prints, success or failure, so a log of
#: several runs stays readable.
Summary = Callable[[str, Path, dict[str, Any]], None]


@dataclass
class StagePlan:
    """One stage to run: its declaration, and the function bound to this run's context."""

    spec: StageSpec
    make: Callable[[StageContext], Any]


def _print_findings(name: str, findings: Sequence[Finding]) -> None:
    for finding in findings:
        print(render_finding(name, finding), file=sys.stderr)


def _portable(path: Path) -> str:
    """A path a reader on another machine can still make sense of.

    The resolved manifest is already free of machine-specific values (feature 001, research R9).
    A report carries a date and a run identifier, so it is not byte-comparable — but an absolute
    path from somebody's home directory is provenance nobody else can use, so it is written
    relative to where the command ran whenever that is possible.
    """
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _stated_train_settings(manifest_path: Path) -> set[str]:
    """Which training settings the author actually wrote, as opposed to inherited.

    Read from the document rather than from the validated manifest, because by the time pydantic
    has filled the defaults in, the two are indistinguishable — and FR-008 asks for exactly that
    distinction.
    """
    from caravan.manifest._yaml import read_mapping

    document = read_mapping(manifest_path)
    section = document.get("train") if isinstance(document, dict) else None
    return set(section) if isinstance(section, dict) else set()


def _dataset_section(dataset: Any, context: StageContext) -> dict[str, Any]:
    section: dict[str, Any] = {
        "root": _portable(dataset.root),
        "files": list(dataset.relative_names),
        "version": dataset.version,
        "total_bytes": dataset.total_bytes,
    }
    records = context.records_if_read
    if records is not None:
        section["records"] = records.schema.record_count
        section["feature_names"] = list(records.schema.feature_names)
    return section


def _artifact(run_dir: Path, name: str) -> dict[str, Any]:
    path = run_dir / name
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:  # pragma: no cover - a stage wrote it, or it is absent
        return {}


#: How many rows of a stage's diagnostic table the summary shows. The whole table is in the file;
#: this is the part a person reads before deciding whether to open it.
DIAGNOSTIC_ROWS = 3


def _print_diagnostic(report: Report) -> None:
    """Show the head of whatever diagnostic a failed gate left behind.

    Written against the shape rather than against the stage, so a later gate that emits a
    per-layer profile gets the same treatment without this function learning about it. The
    constitution asks a failed gate to emit what is needed to act on it; a file nobody mentions is
    not emitted in any useful sense.
    """
    record = report.quantization or {}
    rows = record.get("layer_errors") or []
    if not rows:
        return
    from caravan.convert.debugger import GUIDE_FLAG_LEVEL, REFERENCE_RMSE_OVER_SCALE

    print(
        f"    worst layers by rmse/scale (reference {REFERENCE_RMSE_OVER_SCALE:.3f}, "
        f"the guide flags above {GUIDE_FLAG_LEVEL}):",
        file=sys.stderr,
    )
    for row in rows[:DIAGNOSTIC_ROWS]:
        value = row.get("rmse_over_scale")
        shown = "    —" if value is None else f"{value:6.2f}"
        print(f"      {shown}  {row['op_name']}  {row['tensor_name']}", file=sys.stderr)


def _attach_quantization(report: Report, run_dir: Path) -> None:
    """Fold the quantization record into the report, verdict and all.

    Read from the run directory rather than passed in memory, so the success path and the
    failed-gate path go through the same code: the stage writes the same record either way, and a
    gate's verdict reaches the report the same way whether it passed or not.
    """
    record = _artifact(run_dir, QUANTIZATION_NAME)
    if not record:
        return
    report.quantization = record
    accuracy = record.get("accuracy") or {}
    if "verdict" in accuracy:
        report.gates = (
            *report.gates,
            Gate(
                name="accuracy",
                result=accuracy["verdict"],
                detail=(
                    f"quantization cost {accuracy['quantization_drop']:.3f}, "
                    f"accepted {accuracy['threshold']:.3f} "
                    f"(on {accuracy['samples']} test samples, "
                    f"resolution {accuracy['resolution']:.3f})"
                ),
            ),
        )


def run_pipeline(
    args: argparse.Namespace,
    command: str,
    stages: Sequence[StagePlan],
    summary: Summary,
) -> int:
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
            _print_findings(name, outcome.findings)
            print(f"{name}: invalid — nothing was built", file=sys.stderr)
        run_dir = create_run_directory(Path(args.runs_dir), file_digest(path))
        write_report(run_dir, report_for(command, path, outcome))
        return EXIT_RULE

    # Before anything is written: this installation either can do the work or it cannot.
    if not training_framework_available():
        print(f"{name}: {missing_extra_message(command)}", file=sys.stderr)
        return EXIT_ENVIRONMENT

    assert outcome.manifest is not None
    manifest = outcome.manifest
    resolved = resolve(manifest)

    run_dir = create_run_directory(Path(args.runs_dir), file_digest(path))
    (run_dir / RESOLVED_MANIFEST_NAME).write_text(render_manifest(manifest), encoding="utf-8")
    cache_dir = Path(args.cache_dir)
    report = report_for(
        command,
        path,
        outcome,
        artifacts={"resolved_manifest": RESOLVED_MANIFEST_NAME},
    )

    outcomes: list[StageOutcome] = []
    context: StageContext | None = None
    dataset: Any = None
    try:
        from caravan.data.fingerprint import resolve_dataset

        dataset = resolve_dataset(manifest.dataset.source, path.parent)
        context = StageContext(
            dataset=dataset,
            labels=tuple(manifest.dataset.labels),
            run_dir=run_dir,
            run_id=run_dir.name,
        )

        keys: dict[str, str] = {}
        for plan in stages:
            result = run_stage(
                plan.spec,
                plan.make(context),
                resolved=resolved,
                run_dir=run_dir,
                cache_dir=cache_dir,
                dataset_version=dataset.version,
                upstream_key=keys.get(plan.spec.upstream or ""),
                fresh=args.fresh,
                run_id=run_dir.name,
            )
            keys[plan.spec.name] = result.key
            outcomes.append(result)

    except (RunRuleFailure, EnvironmentIncomplete) as failure:
        report.stages = tuple(outcomes)
        if isinstance(failure, EnvironmentIncomplete):
            # Only reachable if the environment changed under us between the check above and here.
            print(f"{name}: {failure.message}", file=sys.stderr)
            report.outcome = OUTCOME_ERROR
            write_report(run_dir, report)
            return EXIT_ENVIRONMENT
        finding = failure.finding
        report.outcome = OUTCOME_ERROR
        report.findings = (*report.findings, finding)
        report.training = {"finished": False}
        # A stage that failed a gate has already written its record into the run directory, so the
        # verdict and its numbers reach the report on this path too.
        _attach_quantization(report, run_dir)
        write_report(run_dir, report)
        if args.json:
            sys.stdout.write(
                json.dumps(
                    {"manifest": name, "outcome": "invalid", "findings": [finding.as_dict()]},
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n"
            )
        elif not args.quiet:
            _print_findings(name, (finding,))
            _print_diagnostic(report)
            print(f"{name}: the run did not finish", file=sys.stderr)
        return EXIT_RULE

    measured = _artifact(run_dir, METRICS_NAME)
    report.stages = tuple(outcomes)
    assert context is not None and dataset is not None
    report.dataset_resolved = {**_dataset_section(dataset, context), **measured.get("dataset", {})}
    if "training" in measured:
        training = dict(measured["training"])
        stated = _stated_train_settings(path)
        effective = training.get("effective_settings", {})
        # FR-008: the record is complete either way, and this is what makes it *readable* — a
        # reader can see at a glance which numbers the author chose and which ones chose
        # themselves.
        training["settings_from_default"] = sorted(key for key in effective if key not in stated)
        report.training = training
    if "metrics" in measured:
        report.metrics = tuple(QualityMetric(**entry) for entry in measured["metrics"])
    if "confusion_matrix" in measured:
        matrix = measured["confusion_matrix"]
        report.confusion_matrix = ConfusionMatrix(
            labels=tuple(matrix["labels"]),
            rows=tuple(tuple(row) for row in matrix["rows"]),
            split=matrix["split"],
            dataset_version=matrix["dataset_version"],
        )
    _attach_quantization(report, run_dir)
    report.artifacts = {
        "resolved_manifest": RESOLVED_MANIFEST_NAME,
        **{Path(artifact).stem: artifact for stage in outcomes for artifact in stage.artifacts},
    }
    write_report(run_dir, report)

    if args.json:
        sys.stdout.write(
            json.dumps(
                {
                    "manifest": name,
                    "outcome": "valid",
                    "run": str(run_dir),
                    "stages": [stage.as_dict() for stage in outcomes],
                    "metrics": [metric.as_dict() for metric in report.metrics],
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
    elif not args.quiet:
        summary(name, run_dir, measured)
        for stage in outcomes:
            if stage.outcome == cache_module.OUTCOME_REUSED:
                print(
                    f"    {stage.name}: reused the result of run {stage.produced_by_run}",
                    file=sys.stderr,
                )
        print(f"    run: {run_dir}", file=sys.stderr)

    return EXIT_OK
