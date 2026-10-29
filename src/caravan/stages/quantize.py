"""The quantize stage: convert, prove, measure, judge.

Core module — every framework import is inside a function. It is the first stage with a *budget*:
the run's outcome depends on a number the author wrote, so the mechanics of that number are the
design. Three accuracies are measured and the gate judges one difference, for the reason in
``contracts/gate.md``: with a single baseline, accuracy lost in conversion and accuracy lost in
quantization are one number, and a threshold on their sum either fails runs for the wrong reason or
passes them while conversion quietly cost something.
"""

from __future__ import annotations

import json
import math
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from caravan.data.test_part import form_parts
from caravan.env import (
    EnvironmentIncomplete,
    missing_extra_message,
    missing_runtime_message,
    model_runtime_available,
    training_framework_available,
)
from caravan.manifest.errors import (
    RULE_ACCURACY_GATE,
    RULE_GATE_UNMEASURABLE,
    RULE_IMAGE_INPUT_NOT_RAW,
    RULE_NOT_FULLY_QUANTIZED,
    RULE_TRAINED_MODEL_UNREADABLE,
    run_rule_error,
)
from caravan.metrics.anomaly import auc
from caravan.stages._framework import framework_record
from caravan.stages.base import StageContext, StageFunction, StageInputs, StageSpec
from caravan.stages.train import TRAINED_MODEL

QUANTIZED_MODEL = "model/quantized.tflite"
RECORD = "quantization.json"

#: Written straight into the run directory and never declared as an artifact. Both halves of that
#: matter: a failing stage has its working directory deleted by the runner — which is how a failed
#: gate leaves no model behind — so a table written there would be destroyed by the mechanism that
#: protects the artifact; and a declared artifact must be written on every run, while this one
#: exists only for a failure.
ERROR_TABLE = "quantization-error.csv"

#: The one setting that calibrates, and therefore the one with an integer expectation.
CALIBRATED_SETTING = "int8"

#: How many decimals every number here is recorded with, and therefore judged at. One constant,
#: because a verdict computed at a different precision than the record it is written beside is a
#: document that disagrees with itself.
RECORDED_PRECISION = 6

SPEC = StageSpec(
    name="quantize",
    reads=(
        "export.quantization",
        "export.representative_samples",
        "preprocessing.window_size",
        "preprocessing.split",
        "input_features",
        "output_features[0].name",
        "output_features[0].type",
        "output_features[0].preprocessing",
        # The device decision of a binary output, which its gate measures accuracy at.
        "output_features[0].threshold?",
        # The one stage that reads the budget (feature 006 FR-031): changing it re-runs this stage
        # and the export, and never a build or a training. Which one is stated depends on the
        # output type (CF-16).
        "output_features[0].accuracy_drop_max?",
        "output_features[0].mae_increase_max?",
        # Feature 010: an anomaly output's budget, and the percentile its threshold is drawn at.
        "output_features[0].auc_drop_max?",
        "output_features[0].threshold_percentile?",
        "random_seed",
    ),
    reads_dataset=True,
    upstream="train",
    artifacts=(QUANTIZED_MODEL, RECORD),
)


@dataclass(frozen=True)
class CalibrationPlan:
    """Which training samples calibrate the quantization, and what was asked for."""

    requested: int | None
    available: int
    used: int
    seed: int
    indices: tuple[int, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "requested": self.requested,
            "available": self.available,
            "used": self.used,
            "split": "train",
            "seed": self.seed,
        }


def plan_calibration(
    requested: int | None, train_indices: tuple[int, ...], seed: int
) -> CalibrationPlan:
    """Draw calibration samples from the training split, reproducibly and capped.

    ``requested`` is ``None`` for every setting but int8 — the schema makes the count optional and
    rule CF-4 demands it only for int8 — so that is a defined state here and not an oversight.

    Capping rather than refusing when the split holds fewer than the manifest asks for: the arbiter
    of whether calibration was enough is the accuracy gate, which is already there. What is not
    acceptable is silence, so all three counts are recorded.
    """
    available = len(train_indices)
    if requested is None:
        return CalibrationPlan(None, available, 0, seed, ())
    used = min(requested, available)
    chosen = random.Random(seed).sample(sorted(train_indices), used)
    return CalibrationPlan(requested, available, used, seed, tuple(chosen))


@dataclass(frozen=True)
class GateOutcome:
    """The three measurements, the two differences, and the verdict (contracts/gate.md).

    ``metric`` is ``accuracy`` for a ``category`` or ``binary`` output and ``mae`` for a ``number``
    (feature 008, research R5). The change the gate judges is always "how much worse quantization
    made it": accuracy lost, or mean absolute error gained, in the column's unit.
    """

    trained: float
    converted: float
    quantized: float
    threshold: float
    samples: int
    metric: str = "accuracy"

    @property
    def conversion_drop(self) -> float:
        return self.trained - self.converted

    @property
    def quantization_drop(self) -> float:
        return self.converted - self.quantized

    @property
    def change(self) -> float:
        """How much worse quantization made the measurement; negative when it made it better."""
        if self.metric == "mae":
            return self.quantized - self.converted
        return self.quantization_drop

    @property
    def resolution(self) -> float:
        """The smallest accuracy difference this split can express. Recorded with the verdict."""
        return 1.0 / self.samples if self.samples else math.inf

    @property
    def passed(self) -> bool:
        """The verdict, computed from the numbers exactly as the report records them.

        ``<=``: a change equal to the threshold passes. The author wrote the number they accept,
        and a number you accept is one you accept. A negative change — the quantized model doing
        better — passes too, and is reported as negative rather than clamped.

        The rounding is not cosmetic. ``0.90 - 0.88`` is ``0.020000000000000018`` in binary
        floating point, so an unrounded comparison would fail a run whose report says the drop was
        ``0.020000`` and the threshold ``0.02`` — the document would contradict its own verdict.
        Judging the numbers as recorded makes the record and the decision the same thing.
        """
        return round(self.change, RECORDED_PRECISION) <= round(self.threshold, RECORDED_PRECISION)

    def as_dict(self) -> dict[str, Any]:
        if self.metric == "mae":
            return {
                "trained": round(self.trained, RECORDED_PRECISION),
                "converted": round(self.converted, RECORDED_PRECISION),
                "quantized": round(self.quantized, RECORDED_PRECISION),
                "conversion_increase": round(self.converted - self.trained, RECORDED_PRECISION),
                "mae_increase": round(self.change, RECORDED_PRECISION),
                "threshold": self.threshold,
                "verdict": "pass" if self.passed else "fail",
                "samples": self.samples,
            }
        return {
            "trained": round(self.trained, RECORDED_PRECISION),
            "converted": round(self.converted, RECORDED_PRECISION),
            "quantized": round(self.quantized, RECORDED_PRECISION),
            "conversion_drop": round(self.conversion_drop, RECORDED_PRECISION),
            "quantization_drop": round(self.quantization_drop, RECORDED_PRECISION),
            "threshold": self.threshold,
            "verdict": "pass" if self.passed else "fail",
            "samples": self.samples,
            # The step of an accuracy; an AUC moves in steps of one normal-abnormal pair instead,
            # recorded with its counts by the anomaly record (feature 010).
            **(
                {"resolution": round(self.resolution, RECORDED_PRECISION)}
                if self.metric == "accuracy"
                else {}
            ),
        }

    def gate(self) -> dict[str, Any]:
        """The common shape of every gate: what was measured, how it moved, against what budget."""
        return {
            "metric": self.metric,
            "trained": round(self.trained, RECORDED_PRECISION),
            "quantized": round(self.quantized, RECORDED_PRECISION),
            "change": round(self.change, RECORDED_PRECISION),
            "budget": self.threshold,
            "verdict": "pass" if self.passed else "fail",
            "samples": self.samples,
        }

    def summary(self) -> str:
        if self.metric == "mae":
            return (
                f"quantization raised the mean absolute error by {self.change:.3f}, "
                f"accepted {self.threshold:.3f}"
            )
        return f"quantization cost {self.quantization_drop:.3f}, accepted {self.threshold:.3f}"


def require_parts(command: str) -> None:
    """Both halves, with the message that fits whichever is missing."""
    if not training_framework_available():
        raise EnvironmentIncomplete(missing_extra_message(command, extras=("train", "verify")))
    if not model_runtime_available():
        raise EnvironmentIncomplete(missing_runtime_message(command))


def load_trained(run_dir: Path) -> Any:
    """Load what the training stage produced, or refuse with Q-1.

    A *missing* file cannot occur: the runner runs the upstream stage first, and a cache entry
    whose artifacts are absent counts as a miss. What can happen is a file that is there and will
    not load, which is what this rule is for.
    """
    import keras

    # The preprocessing layers are registered on import; a model that carries them loads only then.
    import caravan.templates.builders.preprocessing  # noqa: F401

    path = run_dir / TRAINED_MODEL
    try:
        return keras.saving.load_model(path)
    except Exception as error:
        run_rule_error(
            RULE_TRAINED_MODEL_UNREADABLE,
            "model.template",
            (
                f"the trained model at {TRAINED_MODEL} could not be read ({error}); it is the "
                "artifact the train stage produces, so re-run with --fresh to rebuild it"
            ),
            found=str(path.name),
        )


def score(output: dict[str, Any], raw: Any, targets: Any) -> float:
    """The gate's measurement of one set of raw outputs: accuracy, the mean absolute error, or the
    area under the ROC curve of an anomaly score (feature 010)."""
    import numpy as np

    if output["type"] == "anomaly":
        normal, abnormal = split_scores(raw, targets)
        area = auc(normal, abnormal)
        if area is None:
            run_rule_error(
                RULE_GATE_UNMEASURABLE,
                "output_features[0].auc_drop_max",
                (
                    f"the test part holds {len(normal)} normal and {len(abnormal)} abnormal "
                    "windows; the area under the ROC curve needs both, so the gate cannot decide "
                    "and unknown is not within budget"
                ),
                found={"normal": len(normal), "abnormal": len(abnormal)},
            )
        return float(area)
    if output["type"] == "number":
        return float(np.mean(np.abs(raw.reshape(-1) - targets)))
    if output["type"] == "category":
        predicted = np.argmax(raw, axis=1)
    else:
        predicted = (raw.reshape(-1) >= float(output["threshold"])).astype(np.int64)
        targets = targets.astype(np.int64)
    return float((predicted == targets).sum() / len(targets))


#: The gate's metric and the manifest key of its budget, per output type.
GATE_METRICS = {
    "category": ("accuracy", "accuracy_drop_max"),
    "binary": ("accuracy", "accuracy_drop_max"),
    "number": ("mae", "mae_increase_max"),
    "anomaly": ("auc", "auc_drop_max"),
}


def split_scores(raw: Any, targets: Any) -> tuple[list[float], list[float]]:
    """An anomaly model's scores, divided into normal (target 0) and abnormal (target 1)."""
    scores = [float(value) for value in raw.reshape(-1)]
    normal = [value for value, target in zip(scores, targets, strict=True) if int(target) == 0]
    abnormal = [value for value, target in zip(scores, targets, strict=True) if int(target) == 1]
    return normal, abnormal


def output_of(inputs: StageInputs) -> dict[str, Any]:
    """The output feature with its budget, from the projection."""
    kind = inputs["output_features[0].type"]
    metric, key = GATE_METRICS[kind]
    return {
        "name": inputs["output_features[0].name"],
        "type": kind,
        "preprocessing": inputs["output_features[0].preprocessing"],
        "threshold": inputs.get("output_features[0].threshold") or 0.5,
        "threshold_percentile": inputs.get("output_features[0].threshold_percentile"),
        "budget": float(inputs[f"output_features[0].{key}"]),
        "budget_key": key,
        "metric": metric,
    }


def image_inputs(inputs: StageInputs) -> list[dict[str, Any]]:
    """The model's image inputs, which the converter turns into raw uint8 pixels (feature 010)."""
    return [feature for feature in inputs["input_features"] if feature["type"] == "image"]


def check_raw_pixels(inspection: Any, images: list[dict[str, Any]]) -> None:
    """Q-6: an image input must take the camera's bytes as they are — uint8, scale 1, zero 0.

    Research R6 shows how the converter is brought there; this reads the file to prove it was,
    because the contract tells a firmware author to pass raw pixels.
    """
    names = {feature["name"] for feature in images}
    for tensor in inspection.inputs:
        name = tensor.name.removeprefix("serving_default_").split(":")[0]
        if name not in names:
            continue
        if tensor.dtype != "uint8" or tensor.scale != 1.0 or (tensor.zero_point or 0) != 0:
            run_rule_error(
                RULE_IMAGE_INPUT_NOT_RAW,
                "export.quantization",
                (
                    f"the converted model's image input {name!r} is {tensor.dtype} with scale "
                    f"{tensor.scale} and zero point {tensor.zero_point}; raw pixels need uint8, "
                    "scale 1 and zero point 0, so the device would have to rescale every frame"
                ),
                found={
                    "dtype": tensor.dtype,
                    "scale": tensor.scale,
                    "zero_point": tensor.zero_point,
                },
            )


def stage(context: StageContext) -> StageFunction:
    """The stage function, bound to this run's dataset."""

    def run(inputs: StageInputs, out_dir: Path) -> None:
        require_parts("quantize")

        from caravan.convert.tflite import convert
        from caravan.runtime.inspect import inspect_model
        from caravan.runtime.measure import run_model

        setting = inputs["export.quantization"]
        output = output_of(inputs)
        seed = int(inputs["random_seed"])

        # The same windows, samples and split as the export's test windows (feature 009).
        parts = form_parts(context.records(), inputs, output)
        split, features = parts.split, parts.features

        calibration = plan_calibration(inputs["export.representative_samples"], split.train, seed)
        images = image_inputs(inputs)
        representative = (
            _representative(features, calibration, bounds=bool(images))
            if calibration.used
            else None
        )

        model = load_trained(context.run_dir)
        blob = convert(model, setting, representative, pixel_inputs=bool(images))
        (out_dir / "model").mkdir(parents=True, exist_ok=True)
        quantized_path = out_dir / QUANTIZED_MODEL
        quantized_path.write_bytes(blob)

        # What was produced is established by reading the file, never from the converter: it prints
        # `fully_quantize: 0` for a model whose every tensor is an integer.
        inspection = inspect_model(quantized_path)
        if setting == CALIBRATED_SETTING and not inspection.fully_integer:
            run_rule_error(
                RULE_NOT_FULLY_QUANTIZED,
                "export.quantization",
                (
                    "the manifest asks for int8 but the produced model keeps floating-point "
                    f"tensors: {', '.join(inspection.floating_tensors()[:5])}"
                ),
                found=inspection.dtype_counts,
            )

        if images and setting == CALIBRATED_SETTING:
            check_raw_pixels(inspection, images)

        test_features, test_targets = parts.test()
        if len(test_targets) == 0:  # pragma: no cover - feature 002 refuses an empty split first
            run_rule_error(
                RULE_GATE_UNMEASURABLE,
                "preprocessing.split.probabilities",
                "the test split has no samples, so the int8 gate cannot be shown to hold",
            )

        budget_path = f"output_features[0].{output['budget_key']}"
        with tempfile.TemporaryDirectory() as scratch:
            # The unquantized conversion exists only to produce the baseline the gate judges
            # against, so it is not an artifact: keeping it would invite the question of which
            # model to deploy. Its number is recorded, which is what it is for.
            float_path = Path(scratch) / "converted-float.tflite"
            float_path.write_bytes(convert(model, "none", pixel_inputs=False))
            try:
                converted_raw = run_model(float_path, test_features, output["name"])
                quantized_raw = run_model(quantized_path, test_features, output["name"])
            except ValueError as error:
                run_rule_error(
                    RULE_GATE_UNMEASURABLE,
                    budget_path,
                    f"the comparison could not be measured ({error}); unknown is not within budget",
                )

        trained_raw = model.predict(test_features, verbose=0)[output["name"]]
        gate = GateOutcome(
            trained=score(output, trained_raw, test_targets),
            converted=score(output, converted_raw, test_targets),
            quantized=score(output, quantized_raw, test_targets),
            threshold=output["budget"],
            samples=len(test_targets),
            metric=output["metric"],
        )

        record: dict[str, Any] = {
            "model": {
                "path": QUANTIZED_MODEL,
                "setting": setting,
                "trained_size_bytes": (context.run_dir / TRAINED_MODEL).stat().st_size,
                **inspection.as_dict(),
            },
            "calibration": {
                **calibration.as_dict(),
                # The black and the white frame that pin an image input to raw pixels (R6).
                **({"bounds_frames": BOUNDS_FRAMES} if images and calibration.used else {}),
            },
            "gate": {**gate.gate(), "split": "test", "dataset_version": context.dataset.version},
            output["metric"]: {**gate.as_dict(), "dataset_version": context.dataset.version},
            "tools": {
                **framework_record(),
                "runtime": {"name": "ai-edge-litert", "version": _runtime_version()},
            },
        }
        if output["type"] == "anomaly":
            record.update(
                anomaly_record(output, parts, quantized_path, quantized_raw, test_targets)
            )
            record["auc"].update(
                {
                    "normal": int((test_targets == 0).sum()),
                    "abnormal": int((test_targets == 1).sum()),
                }
            )
        if output["type"] == "category":
            labels = len(output["preprocessing"]["fitted"]["labels"])
            record["accuracy"]["confusion_quantized"] = _confusion(
                quantized_raw, test_targets, labels
            )

        if not gate.passed:
            # The record and the table go straight into the run directory: this stage is about to
            # raise, and the runner will delete the working directory with the model in it.
            order = [
                tensor.name.removeprefix("serving_default_").split(":")[0]
                for tensor in inspection.inputs
            ]
            rows = _layer_errors(model, representative, order)
            record["layer_errors"] = [row.as_dict() for row in rows]
            _write_failure(context.run_dir, record, rows)
            detail = (
                f"On {gate.samples} test samples one changed prediction is {gate.resolution:.3f}; "
                if output["metric"] == "accuracy"
                else f"Measured on {gate.samples} test samples; "
            )
            run_rule_error(
                RULE_ACCURACY_GATE,
                budget_path,
                (
                    f"the int8 gate failed — {gate.summary()}. {detail}no model was written and "
                    f"the per-layer table is in {ERROR_TABLE}"
                ),
                found=gate.as_dict(),
            )

        (out_dir / RECORD).write_text(
            json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return run


def _confusion(raw: Any, targets: Any, labels: int) -> list[list[int]]:
    import numpy as np

    matrix = np.zeros((labels, labels), dtype=np.int64)
    for actual, guess in zip(targets, np.argmax(raw, axis=1), strict=True):
        matrix[int(actual), int(guess)] += 1
    return [[int(cell) for cell in row] for row in matrix]


#: How many frames are put before the training samples to calibrate an image input: one black, one
#: white (feature 010, research R6).
BOUNDS_FRAMES = 2


def _representative(features: Any, calibration: CalibrationPlan, *, bounds: bool = False) -> Any:
    """A generator over the chosen training samples: one dict per sample, keyed by input name.

    With ``bounds``, one black and one white frame come first. Calibration sets an input's scale
    from the range it sees, and real images need not hold a pixel at 0 and one at 255; without the
    two frames the measured scale was 0.941, and the device would have had to rescale every frame
    (research R6). With them, the converted input takes the camera's bytes as they are.
    """
    import numpy as np

    def generate():
        if bounds:
            for value in (0.0, 255.0):
                yield {
                    name: np.full((1, *values.shape[1:]), value, dtype=np.float32)
                    for name, values in features.items()
                }
        for index in calibration.indices:
            yield {name: values[index : index + 1] for name, values in features.items()}

    return generate


def anomaly_record(
    output: dict[str, Any], parts: Any, quantized_path: Path, quantized_raw: Any, test_targets: Any
) -> dict[str, Any]:
    """The alarm threshold, and what it catches on the test part (feature 010, research R10).

    The threshold is a percentile of the **int8** model's scores on the validation part's normal
    windows: the device runs the int8 model, and a threshold from the float model's scores would be
    on another scale. The rates are measured with the same int8 model on the test part.
    """
    from caravan.data.reader_bridge import select
    from caravan.metrics.anomaly import detection, percentile
    from caravan.runtime.measure import run_model

    normal_val = [index for index in parts.split.val if int(parts.targets[index]) == 0]
    percent = float(output["threshold_percentile"])
    scores = run_model(quantized_path, select(parts.features, normal_val), output["name"])
    threshold = round(percentile([float(value) for value in scores.reshape(-1)], percent), 6)
    normal, abnormal = split_scores(quantized_raw, test_targets)
    rates = detection(normal, abnormal, threshold)
    return {
        "threshold": {
            "rule": "percentile",
            "percentile": percent,
            "value": threshold,
            "computed_on": "int8 scores of the validation part's normal windows",
            "windows": len(normal_val),
        },
        "detection": {
            "split": "test",
            "abnormal_when": "score >= threshold",
            **{key: None if value is None else round(value, 6) for key, value in rates.items()},
        },
    }


def _runtime_version() -> str:
    from importlib.metadata import version

    try:
        return version("ai-edge-litert")
    except Exception:  # pragma: no cover - installed by definition at this point
        return "unknown"


def _layer_errors(model: Any, representative: Any, order: list[str]) -> tuple[Any, ...]:
    """The diagnostic table, which only a failure pays for."""
    if representative is None:
        return ()
    from caravan.convert.debugger import layer_errors

    return layer_errors(model, representative, order)


def _write_failure(run_dir: Path, record: dict[str, Any], rows: tuple[Any, ...]) -> None:
    from caravan.convert.debugger import write_table

    (run_dir / RECORD).write_text(
        json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if rows:
        write_table(run_dir / ERROR_TABLE, rows)
