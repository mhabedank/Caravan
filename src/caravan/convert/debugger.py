"""The per-layer quantization error table, for a failed gate.

Produced only when the accuracy gate fails (FR-016). It costs a second, instrumented conversion
and one inference per calibration sample, so a routine cost on every successful run would be paid
by everyone to serve nobody — and a passing run has nothing to act on.

The ranking value is ``rmse / scale``. From the LiteRT quantization-debugger guide: it "is close to
``1 / sqrt(12)`` (~ 0.289) when quantized distribution is similar", and "the larger the value is,
it's more likely for the layer not being quantized well". The guide's own example flags layers above
0.7. Neither number is a gate here — the gate is the author's threshold, and these are the evidence
that lets them act on it.
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tensorflow as tf

#: What a well-quantized tensor's rmse/scale sits near, and what the vendor's own example treats as
#: worth acting on. Reported with every table, because a number without its reference is not yet
#: information.
REFERENCE_RMSE_OVER_SCALE = 1.0 / math.sqrt(12.0)
GUIDE_FLAG_LEVEL = 0.7


@dataclass(frozen=True)
class LayerErrorRow:
    """One layer, and how much its output moved under quantization."""

    op_name: str
    tensor_name: str
    num_elements: int
    rmse: float
    scale: float
    rmse_over_scale: float | None
    max_abs_error: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "op_name": self.op_name,
            "tensor_name": self.tensor_name,
            "num_elements": self.num_elements,
            "rmse": round(self.rmse, 6),
            "scale": self.scale,
            "rmse_over_scale": (
                None if self.rmse_over_scale is None else round(self.rmse_over_scale, 6)
            ),
            "max_abs_error": round(self.max_abs_error, 6),
        }


def _sort_key(row: LayerErrorRow) -> tuple[int, float]:
    # Rows without a ranking value sort last rather than raising: a tensor with no scale is not
    # evidence about quantization, and dropping it would hide a layer the author can see.
    return (0, -row.rmse_over_scale) if row.rmse_over_scale is not None else (1, 0.0)


def layer_errors(model: Any, representative: Any) -> tuple[LayerErrorRow, ...]:
    """Run the debugger and return its rows, worst first."""
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative

    debugger = tf.lite.experimental.QuantizationDebugger(
        converter=converter, debug_dataset=representative
    )
    debugger.run()

    dump = io.StringIO()
    debugger.layer_statistics_dump(dump)
    dump.seek(0)

    rows: list[LayerErrorRow] = []
    for record in csv.DictReader(dump):
        scale = float(record.get("scale") or 0.0)
        rmse = math.sqrt(max(float(record.get("mean_squared_error") or 0.0), 0.0))
        rows.append(
            LayerErrorRow(
                op_name=record.get("op_name", ""),
                tensor_name=record.get("tensor_name", ""),
                num_elements=int(float(record.get("num_elements") or 0)),
                rmse=rmse,
                scale=scale,
                rmse_over_scale=(rmse / scale if scale else None),
                max_abs_error=float(record.get("max_abs_error") or 0.0),
            )
        )
    return tuple(sorted(rows, key=_sort_key))


def write_table(path: Path, rows: tuple[LayerErrorRow, ...]) -> None:
    """Write the table where a person can open it, worst first, with its reference stated."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(
            f"# rmse_over_scale: near {REFERENCE_RMSE_OVER_SCALE:.3f} (1/sqrt(12)) quantizes "
            f"well; the LiteRT guide flags above {GUIDE_FLAG_LEVEL}\n"
        )
        writer = csv.writer(handle)
        writer.writerow(
            [
                "op_name",
                "tensor_name",
                "num_elements",
                "rmse",
                "scale",
                "rmse_over_scale",
                "max_abs_error",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.op_name,
                    row.tensor_name,
                    row.num_elements,
                    f"{row.rmse:.6f}",
                    row.scale,
                    "" if row.rmse_over_scale is None else f"{row.rmse_over_scale:.6f}",
                    f"{row.max_abs_error:.6f}",
                ]
            )
