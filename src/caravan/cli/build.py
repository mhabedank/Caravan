"""``caravan build`` — what does this manifest actually describe?"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from caravan.cli.pipeline import StagePlan, run_pipeline
from caravan.stages import build as build_stage


def _summary(name: str, run_dir: Path, _measured: dict[str, Any]) -> None:
    """The shape report, on standard error, in the form ``contracts/cli.md`` fixes."""
    description = json.loads((run_dir / build_stage.BUILT_REPORT).read_text(encoding="utf-8"))
    inputs = ", ".join(
        f"{entry['name']} {entry['dtype']}[{', '.join(str(size) for size in entry['shape'])}]"
        for entry in description["inputs"]
    )
    units = ", ".join(str(size) for size in description["output_shape"])
    print(
        f"{name}: built {description['template']} — inputs {inputs}; "
        f"output {description['output_name']} ({units}), "
        f"{description['parameter_count']:,} parameters "
        f"({description['trainable_parameters']:,} trainable)",
        file=sys.stderr,
    )
    for layer in description["layers"]:
        width = ", ".join("?" if size is None else str(size) for size in layer["output_shape"][1:])
        print(f"    {layer['name']:<14} ({width})  {layer['parameters']:>8,}", file=sys.stderr)


def run(args: argparse.Namespace) -> int:
    return run_pipeline(
        args,
        "build",
        (StagePlan(spec=build_stage.SPEC, make=build_stage.stage),),
        _summary,
    )
