"""``caravan export`` — the files a firmware author compiles, and what they still owe."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from caravan.cli.pipeline import StagePlan, run_pipeline
from caravan.stages import build as build_stage
from caravan.stages import export as export_stage
from caravan.stages import quantize as quantize_stage
from caravan.stages import train as train_stage


def _summary(name: str, run_dir: Path, _measured: dict[str, Any]) -> None:
    """Read from the artifact the stage wrote, so a reused result prints the same thing."""
    path = run_dir / export_stage.RECORD
    if not path.is_file():  # pragma: no cover - the stage declares it
        return
    record = json.loads(path.read_text(encoding="utf-8"))
    graph = record["graph"]
    memory = graph["working_memory"]

    distinct, nodes = graph["distinct_operators"], graph["nodes"]
    model = next(a for a in record["artifacts"] if a["format"] == "flatbuffer")
    print(
        f"{name}: exported {distinct} operator{'s' if distinct != 1 else ''} in {nodes} "
        f"node{'s' if nodes != 1 else ''} — {model['bytes']:,} bytes",
        file=sys.stderr,
    )
    # Grouped, because three artifacts called main.cc in a row tell a reader nothing: what
    # distinguishes them is the board they are for.
    shared = [a["path"] for a in record["artifacts"] if a.get("target") is None]
    per_target = sorted({a["target"] for a in record["artifacts"] if a.get("target")})
    listed = [Path(path).name for path in shared]
    if per_target:
        listed.append("runner/{" + ",".join(per_target) + "}/main.cc")
    print(f"    artifacts: {', '.join(listed)}", file=sys.stderr)
    print(
        "    operators: " + ", ".join(f"{o['name']} v{o['version']}" for o in graph["operators"]),
        file=sys.stderr,
    )

    verdicts = record["coverage"]
    if verdicts:
        covered = Counter(v["target"] for v in verdicts if v["accelerated"])
        total = Counter(v["target"] for v in verdicts)
        shown = ", ".join(f"{target} {covered[target]} of {total[target]}" for target in total)
        print(f"    accelerated: {shown}", file=sys.stderr)
        falling_back = sorted({v["operator"] for v in verdicts if not v["accelerated"]})
        if falling_back:
            print(
                f"      reference kernels: {', '.join(falling_back)}",
                file=sys.stderr,
            )
    # Two lines, not one. The figure on its own would be read as the arena to configure, which is
    # the one thing this stage is not entitled to say.
    print(
        f"    working memory: floor {memory['floor_bytes']:,} bytes ({memory['floor_method']})",
        file=sys.stderr,
    )
    print(
        "                    the figure a board needs is larger and is measured, not computed here",
        file=sys.stderr,
    )


def run(args: argparse.Namespace) -> int:
    return run_pipeline(
        args,
        "export",
        (
            StagePlan(spec=build_stage.SPEC, make=build_stage.stage),
            StagePlan(spec=train_stage.SPEC, make=train_stage.stage),
            StagePlan(spec=quantize_stage.SPEC, make=quantize_stage.stage),
            StagePlan(spec=export_stage.SPEC, make=export_stage.stage),
        ),
        _summary,
        # Both halves: this verb converts and reads a model, so a message naming only the
        # conversion half would refuse the reader twice.
        extras=("train", "verify"),
    )
