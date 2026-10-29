"""A convolution over a plane of feature frames, from manifest to export (feature 010, US2)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_RULE, main
from caravan.manifest.errors import RULE_ACCURACY_GATE, RULE_WINDOW_MATCHES_TEMPLATE
from caravan.stages.quantize import QUANTIZED_MODEL
from tests.train.conftest import latest_run

REPOSITORY = Path(__file__).resolve().parents[2]
EXAMPLE = REPOSITORY / "examples" / "frames-conv2d.yaml"
BOARDS = ("s32k144", "stm32h743", "esp32")

#: The MLPerf Tiny keyword-spotting reference (mlcommons/tiny, keyword_spotting/keras_model.py,
#: ds_cnn, read 2026-10-29) in this template's terms.
KWS_REFERENCE = {
    "blocks": [
        {"filters": 64, "kernel": [10, 4], "stride": 2, "padding": "same", "normalise": True},
        *[
            {"kind": "separable", "filters": 64, "kernel": 3, "padding": "same", "normalise": True}
            for _ in range(4)
        ],
    ],
    "head": "average",
}


def kws_parameter_count() -> int:
    """The reference's parameters, counted from its architecture rather than from Keras.

    A convolution: kernel elements times input channels times filters, plus one bias per filter.
    A depthwise convolution: kernel elements times channels, plus one bias per channel.
    Normalisation: four values per channel (scale, offset, mean, variance).
    """
    filters, labels = 64, 12
    first = 10 * 4 * 1 * filters + filters + 4 * filters
    separable = (3 * 3 * filters + filters + 4 * filters) + (
        filters * filters + filters + 4 * filters
    )
    head = filters * labels + labels
    return first + 4 * separable + head


def test_the_keyword_spotting_reference_has_its_parameter_count() -> None:
    # SC-006. 24,908: the count of the reference as its code defines it (research R1).
    from caravan.templates.builders import load_builder

    model = load_builder("conv2d")(KWS_REFERENCE, (49, 10), [str(k) for k in range(12)])
    assert kws_parameter_count() == 24_908
    assert model.count_params() == kws_parameter_count()
    assert tuple(model.outputs[0].shape) == (None, 12)


def test_the_average_head_is_a_pooling_over_the_whole_plane() -> None:
    from caravan.templates.builders import load_builder

    model = load_builder("conv2d")(KWS_REFERENCE, (49, 10), ["a", "b"])
    head = model.get_layer("pool_head")
    assert tuple(head.pool_size) == (25, 5)


def test_a_separable_block_is_counted_by_the_fit_stage() -> None:
    from caravan.stages.fit import layer_records
    from caravan.templates.builders import load_builder

    model = load_builder("conv2d")(KWS_REFERENCE, (49, 10), ["a", "b"])
    records = {record.name: record for record in layer_records(model)}
    depthwise = records["depthwise_2"]
    assert depthwise.kind == "conv"
    assert depthwise.kernel_elements == 3 * 3 * 64
    assert depthwise.bias_elements == 64


@pytest.fixture(scope="module")
def exported(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("frames")
    previous = Path.cwd()
    os.chdir(root)
    try:
        code = main(
            [
                "export",
                str(EXAMPLE),
                "--runs-dir",
                str(root / "runs"),
                "--cache-dir",
                str(root / "cache"),
            ]
        )
        assert code == 0
    finally:
        os.chdir(previous)
    return latest_run(root / "runs")


def test_the_example_runs_end_to_end_with_the_gate_passing(exported) -> None:
    built = json.loads((exported / "model" / "built.json").read_text(encoding="utf-8"))
    names = [layer["name"] for layer in built["layers"]]
    assert "plane" in names and "depthwise_2" in names
    gate = json.loads((exported / "quantization.json").read_text(encoding="utf-8"))["gate"]
    assert gate["verdict"] == "pass"


def test_every_operator_is_resolvable_and_the_convolutions_are_accelerated(exported) -> None:
    # SC-007: a resolver method and a coverage verdict for every operator on every board.
    from caravan.export.methods import method_for

    record = json.loads((exported / "export.json").read_text(encoding="utf-8"))
    operators = [operator["name"] for operator in record["graph"]["operators"]]
    assert all(method_for(name) for name in operators)
    verdicts = {(v["target"], v["operator"]): v["accelerated"] for v in record["coverage"]}
    assert set(verdicts) == {(board, name) for board in BOARDS for name in operators}
    for name in ("CONV_2D", "DEPTHWISE_CONV_2D", "AVERAGE_POOL_2D"):
        assert name in operators
        assert all(verdicts[(board, name)] for board in BOARDS)


def test_an_axis_learned_from_the_data_is_still_checked_before_training(
    tmp_path, workspace
) -> None:
    # A one-hot category's width is known only once its vocabulary is fitted; validation lets the
    # manifest through, and the build stage refuses it with CF-6 before any training.
    data = tmp_path / "data"
    data.mkdir()
    rows = ["label,a,gear"] + [
        f"{('x', 'y')[index // 12 % 2]},{index % 7},{('p', 'q')[index % 2]}" for index in range(480)
    ]
    (data / "records.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    manifest = tmp_path / "probe.yaml"
    manifest.write_text(
        f"""apiVersion: caravan/v0.2
model:
  name: probe
  version: 0.0.1
  template: conv2d
  params:
    blocks: [{{filters: 4, kernel: [3, 9]}}]
input_features:
  - {{name: a, type: number}}
  - {{name: gear, type: category, encoder: {{type: onehot}}}}
output_features:
  - {{name: label, type: category, accuracy_drop_max: 0.05}}
preprocessing: {{window_size: 12}}
dataset: {data}
export: {{targets: [stm32h743], representative_samples: 100}}
""",
        encoding="utf-8",
    )
    runs, cache = workspace
    code = main(["train", str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])
    assert code == EXIT_RULE
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    finding = next(f for f in report["findings"] if f.get("rule") == RULE_WINDOW_MATCHES_TEMPLATE)
    assert "columns axis has 4 columns" in finding["problem"]
    assert not (latest_run(runs) / "model" / "trained.keras").exists()


def test_a_lost_accuracy_fails_the_gate_and_leaves_no_model(workspace, monkeypatch) -> None:
    # SC-002 for this template: the gate can fail. On the fixture int8 loses nothing, so the loss
    # is injected at the measurement seam, as feature 003's gate test does.
    from tests.train.test_gate_failure import degrade_the_quantized_model

    degrade_the_quantized_model(monkeypatch)
    runs, cache = workspace
    code = main(["quantize", str(EXAMPLE), "--runs-dir", str(runs), "--cache-dir", str(cache)])
    assert code == EXIT_RULE
    report = json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))
    finding = next(f for f in report["findings"] if f.get("rule") == RULE_ACCURACY_GATE)
    assert finding["path"] == "output_features[0].accuracy_drop_max"
    assert not (latest_run(runs) / QUANTIZED_MODEL).exists()
