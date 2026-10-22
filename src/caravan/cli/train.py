"""``caravan train`` — the model the manifest describes, trained on the data it names."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from caravan.cli.pipeline import StagePlan, run_pipeline
from caravan.stages import build as build_stage
from caravan.stages import train as train_stage


def _summary(name: str, _run_dir: Path, measured: dict[str, Any]) -> None:
    """The result, with what every number was measured against (FR-007)."""
    training = measured.get("training", {})
    settings = training.get("effective_settings", {})
    stopped = (
        f", stopped early at {training.get('stopped_epoch')}"
        if training.get("stopped_early")
        else ""
    )
    print(
        f"{name}: trained — {training.get('epochs_run')} of {settings.get('epochs')} "
        f"epochs{stopped} (best: {training.get('best_epoch')})",
        file=sys.stderr,
    )

    by_name = {(metric["name"], metric["split"]): metric for metric in measured.get("metrics", ())}
    accuracy = by_name.get(("accuracy", "test"))
    f1 = by_name.get(("f1_macro", "test"))
    if accuracy is not None:
        # The split, the sample count and the dataset version travel with the number, on the same
        # line, because a quality figure without them is not a result.
        print(
            f"    test, {accuracy['samples']} windows, dataset "
            f"{accuracy['dataset_version'][:18]}…  accuracy {accuracy['value']:.3f}"
            + (f"  f1_macro {f1['value']:.3f}" if f1 is not None else ""),
            file=sys.stderr,
        )
    per_class = by_name.get(("recall_per_class", "test"))
    if per_class is not None:
        recalls = "  ".join(f"{label} {value:.3f}" for label, value in per_class["value"].items())
        print(f"    recall: {recalls}", file=sys.stderr)


def run(args: argparse.Namespace) -> int:
    return run_pipeline(
        args,
        "train",
        (
            StagePlan(spec=build_stage.SPEC, make=build_stage.stage),
            StagePlan(spec=train_stage.SPEC, make=train_stage.stage),
        ),
        _summary,
    )
