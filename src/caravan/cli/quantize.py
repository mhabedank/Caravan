"""``caravan quantize`` — the deployable model, or the reason there isn't one."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from caravan.cli.pipeline import StagePlan, run_pipeline
from caravan.stages import build as build_stage
from caravan.stages import quantize as quantize_stage
from caravan.stages import train as train_stage


def _summary(name: str, run_dir: Path, _measured: dict[str, Any]) -> None:
    """The record, read from the artifact the stage wrote, so reuse prints the same thing."""
    path = run_dir / quantize_stage.RECORD
    if not path.is_file():  # pragma: no cover - the stage declares it
        return
    record = json.loads(path.read_text(encoding="utf-8"))
    model, calibration, accuracy = record["model"], record["calibration"], record["accuracy"]

    counts = ", ".join(f"{dtype} {count}" for dtype, count in model["dtype_counts"].items())
    integer = "fully integer" if model["fully_integer"] else "not fully integer"
    print(
        f"{name}: quantized {model['setting']} — {model['size_bytes']:,} bytes from "
        f"{model['trained_size_bytes']:,} ({model['path']})",
        file=sys.stderr,
    )
    scale = model["input"].get("scale")
    detail = f", input {model['input']['dtype']}" + (f" scale {scale:.6f}" if scale else "")
    print(f"    tensors: {counts} — {integer}{detail}", file=sys.stderr)
    requested = calibration["requested"]
    if requested is None:
        print(
            f"    calibration: none — {model['setting']} calibrates against nothing",
            file=sys.stderr,
        )
    else:
        print(
            f"    calibration: {calibration['used']} of {requested} requested, drawn from "
            f"{calibration['available']} available in the {calibration['split']} split, "
            f"seed {calibration['seed']}",
            file=sys.stderr,
        )
    version = accuracy["dataset_version"][:18]
    print(f"    test, {accuracy['samples']} windows, dataset {version}…", file=sys.stderr)
    print(
        f"      trained {accuracy['trained']:.3f}  converted {accuracy['converted']:.3f}  "
        f"quantized {accuracy['quantized']:.3f}",
        file=sys.stderr,
    )
    print(
        f"      conversion cost {accuracy['conversion_drop']:.3f}  "
        f"quantization cost {accuracy['quantization_drop']:.3f}  "
        f"accepted {accuracy['threshold']:.3f}  → {accuracy['verdict']}",
        file=sys.stderr,
    )


def run(args: argparse.Namespace) -> int:
    return run_pipeline(
        args,
        "quantize",
        (
            StagePlan(spec=build_stage.SPEC, make=build_stage.stage),
            StagePlan(spec=train_stage.SPEC, make=train_stage.stage),
            StagePlan(spec=quantize_stage.SPEC, make=quantize_stage.stage),
        ),
        _summary,
    )
