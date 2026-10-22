"""How the per-layer table is ordered, and the reference that travels with it."""

from __future__ import annotations

import math

import pytest

litert_debugger = pytest.importorskip(
    "caravan.convert.debugger",
    reason="the ranking lives beside the debugger, which needs the conversion half",
)

LayerErrorRow = litert_debugger.LayerErrorRow


def row(name: str, rmse: float, scale: float) -> LayerErrorRow:
    return LayerErrorRow(
        op_name=name,
        tensor_name=f"{name}/out",
        num_elements=10,
        rmse=rmse,
        scale=scale,
        rmse_over_scale=(rmse / scale if scale else None),
        max_abs_error=rmse * 2,
    )


def test_rows_order_worst_first() -> None:
    rows = sorted(
        [row("a", 0.1, 1.0), row("b", 0.9, 1.0), row("c", 0.5, 1.0)],
        key=litert_debugger._sort_key,
    )
    assert [r.op_name for r in rows] == ["b", "c", "a"]


def test_a_row_without_a_scale_sorts_last_rather_than_raising() -> None:
    # A tensor with no scale is not evidence about quantization, and dropping it would hide a
    # layer the author can see.
    rows = sorted([row("none", 0.5, 0.0), row("worst", 0.2, 1.0)], key=litert_debugger._sort_key)
    assert [r.op_name for r in rows] == ["worst", "none"]
    assert rows[-1].rmse_over_scale is None


def test_the_reference_is_one_over_root_twelve() -> None:
    # From the LiteRT quantization-debugger guide: rmse/scale near 1/sqrt(12) means the quantized
    # distribution is similar, and the larger it is the worse the layer quantized.
    assert pytest.approx(1 / math.sqrt(12)) == litert_debugger.REFERENCE_RMSE_OVER_SCALE
    assert pytest.approx(0.2887, abs=1e-4) == litert_debugger.REFERENCE_RMSE_OVER_SCALE
    assert litert_debugger.GUIDE_FLAG_LEVEL == 0.7


def test_the_table_carries_its_reference_into_the_file(tmp_path) -> None:
    path = tmp_path / "errors.csv"
    litert_debugger.write_table(path, (row("a", 0.9, 1.0), row("b", 0.1, 0.0)))
    text = path.read_text(encoding="utf-8")
    # A number without its reference is not yet information, so the file carries both.
    assert "0.289" in text and "0.7" in text
    assert text.splitlines()[1].startswith("op_name")
    assert "a," in text and "b," in text
