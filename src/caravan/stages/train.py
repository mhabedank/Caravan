"""The train stage: the model, the data, and the numbers that describe the result.

Core module — every framework import is inside a function, so importing it loads no framework.

One thing here is the feature's honesty, not its mechanics: a diverged run leaves nothing behind
(DS-10, FR-012) — no trained model, no best checkpoint — because the stage writes into a private
directory that is only published if it finishes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from caravan.data.reader_bridge import assemble_samples, select
from caravan.data.windows import plan_windows, split_for
from caravan.manifest.errors import RULE_TRAINING_DIVERGED, run_rule_error
from caravan.stages._framework import framework_record
from caravan.stages.base import StageContext, StageFunction, StageInputs, StageSpec
from caravan.stages.build import load_built_model, require_framework
from caravan.stages.data import split_labels

TRAINED_MODEL = "model/trained.keras"
BEST_CHECKPOINT = "checkpoints/best.keras"
FINAL_CHECKPOINT = "checkpoints/final.keras"
METRICS = "metrics.json"
HISTORY = "training-history.json"

#: The value the best checkpoint is chosen by. Validation loss rather than validation accuracy: on
#: a small validation split accuracy moves in steps of 1/n and ties constantly, and the tie-break
#: would silently become "the last epoch".
MONITOR = "val_loss"

SPEC = StageSpec(
    name="train",
    # Every field this stage reads, and nothing else — it receives a projection of exactly this
    # tuple. The features (with their fitted values) and the window form the samples; the split
    # and the seed choose the training part; the output's type and loss decide what is learned.
    # Never the budget: it is read by ``quantize`` alone, so changing it must not retrain
    # (Principle III, feature 006 FR-031).
    reads=(
        "trainer.epochs",
        "trainer.batch_size",
        "trainer.learning_rate",
        "trainer.optimizer",
        "trainer.early_stop",
        "random_seed",
        "preprocessing.window_size",
        "preprocessing.split",
        "input_features",
        "output_features[0].name",
        "output_features[0].type",
        "output_features[0].preprocessing",
        "output_features[0].loss",
    ),
    reads_dataset=True,
    upstream="build",
    artifacts=(TRAINED_MODEL, BEST_CHECKPOINT, FINAL_CHECKPOINT, METRICS, HISTORY),
)

#: Ludwig's names for the losses of a ``number`` output, as Keras knows them.
NUMBER_LOSSES = {
    "mean_squared_error": "mean_squared_error",
    "mean_absolute_error": "mean_absolute_error",
    "huber": "huber",
}


class Diverged(Exception):
    """Raised from inside the training loop when the loss stops being a number."""

    def __init__(self, epoch: int, value: object) -> None:
        super().__init__(f"the loss became {value} at epoch {epoch}")
        self.epoch = epoch
        self.value = value


def _optimizer(name: str, learning_rate: float) -> Any:
    import keras

    builders = {
        "adam": keras.optimizers.Adam,
        "adamw": keras.optimizers.AdamW,
        "sgd": keras.optimizers.SGD,
    }
    return builders[name](learning_rate=learning_rate)


def _divergence_guard() -> Any:
    import keras

    class StopOnNonFiniteLoss(keras.callbacks.Callback):
        """A diverged run is a failed run, not a model with a strange loss (FR-012)."""

        def on_epoch_end(self, epoch, logs=None):  # the framework's own signature
            import math

            value = (logs or {}).get("loss")
            if value is None or not math.isfinite(float(value)):
                raise Diverged(epoch + 1, value)

    return StopOnNonFiniteLoss()


def output_of(inputs: StageInputs) -> dict[str, Any]:
    """The output feature, from the projection."""
    return {
        "name": inputs["output_features[0].name"],
        "type": inputs["output_features[0].type"],
        "preprocessing": inputs["output_features[0].preprocessing"],
        "loss": inputs.get("output_features[0].loss") or {},
    }


def loss_and_metrics(output: dict[str, Any]) -> tuple[Any, list[str]]:
    """What is minimised and what is watched, per output type (research R5)."""
    if output["type"] == "category":
        return "sparse_categorical_crossentropy", ["accuracy"]
    if output["type"] == "binary":
        return "binary_crossentropy", ["binary_accuracy"]
    return NUMBER_LOSSES[output["loss"].get("type") or "mean_squared_error"], [
        "mean_absolute_error"
    ]


def sample_weights(output: dict[str, Any], targets: Any) -> Any:
    """Per-sample weights from ``class_weights`` or ``positive_class_weight``; ``None`` without."""
    import numpy as np

    loss = output["loss"]
    if output["type"] == "category" and loss.get("class_weights") is not None:
        stated = loss["class_weights"]
        labels = output["preprocessing"]["fitted"]["labels"]
        weights = (
            [float(stated.get(label, 1.0)) for label in labels]
            if isinstance(stated, dict)
            else [float(value) for value in stated]
        )
        return np.asarray(weights, dtype=np.float32)[targets.astype(np.int64)]
    if output["type"] == "binary" and loss.get("positive_class_weight") is not None:
        weight = float(loss["positive_class_weight"])
        return np.where(targets > 0.5, weight, 1.0).astype(np.float32)
    return None


def stage(context: StageContext) -> StageFunction:
    """The stage function, bound to this run's dataset."""

    def run(inputs: StageInputs, out_dir: Path) -> None:
        require_framework("train")

        import keras

        output = output_of(inputs)
        name = output["name"]
        seed = int(inputs["random_seed"])
        keras.utils.set_random_seed(seed)

        records = context.records()
        window_plan = plan_windows(
            records.labels, inputs["preprocessing.window_size"], parts=records.parts
        )
        split = split_for(
            window_plan,
            inputs["preprocessing.split"],
            seed=seed,
            labels=split_labels(output["type"], window_plan.labels),
        )
        features, targets = assemble_samples(
            records, window_plan, inputs["input_features"], output
        )

        # The build stage's artifacts are already in the run directory, whether this run
        # produced them or reused them from the cache.
        model = load_built_model(context.run_dir)
        loss, metrics = loss_and_metrics(output)
        # The model returns a dict keyed by the output's name, so the loss and the targets are
        # keyed the same way.
        model.compile(
            optimizer=_optimizer(
                inputs["trainer.optimizer"]["type"], float(inputs["trainer.learning_rate"])
            ),
            loss={name: loss},
            metrics={name: metrics},
        )

        (out_dir / "model").mkdir(parents=True, exist_ok=True)
        (out_dir / "checkpoints").mkdir(parents=True, exist_ok=True)

        callbacks = [
            keras.callbacks.ModelCheckpoint(
                filepath=str(out_dir / BEST_CHECKPOINT),
                monitor=MONITOR,
                save_best_only=True,
                save_weights_only=False,
            ),
            _divergence_guard(),
        ]
        patience = int(inputs["trainer.early_stop"])
        if patience >= 0:
            callbacks.append(
                keras.callbacks.EarlyStopping(
                    monitor=MONITOR, patience=patience, restore_best_weights=True
                )
            )

        train_targets = targets[list(split.train)]
        weights = sample_weights(output, train_targets)
        try:
            history = model.fit(
                select(features, split.train),
                {name: train_targets},
                sample_weight=None if weights is None else {name: weights},
                validation_data=(select(features, split.val), {name: targets[list(split.val)]}),
                epochs=int(inputs["trainer.epochs"]),
                batch_size=int(inputs["trainer.batch_size"]),
                callbacks=callbacks,
                shuffle=True,
                verbose=0,
            )
        except Diverged as diverged:
            run_rule_error(
                RULE_TRAINING_DIVERGED,
                "trainer.learning_rate",
                (
                    f"training diverged: {diverged}. No model was written. A learning rate this "
                    "size is where to look"
                ),
                found={"epoch": diverged.epoch, "loss": str(diverged.value)},
            )

        model.save(out_dir / TRAINED_MODEL)
        model.save(out_dir / FINAL_CHECKPOINT)
        if not (out_dir / BEST_CHECKPOINT).exists():  # pragma: no cover - one-epoch runs
            model.save(out_dir / BEST_CHECKPOINT)

        epochs_run = len(history.history.get("loss", []))
        monitored = history.history.get(MONITOR, [])
        best_epoch = (
            int(min(range(len(monitored)), key=lambda index: monitored[index])) + 1
            if monitored
            else epochs_run
        )
        stopped_early = epochs_run < int(inputs["trainer.epochs"])

        _write_measurements(
            out_dir,
            model=model,
            features=features,
            targets=targets,
            split=split,
            window_plan=window_plan,
            records=records,
            output=output,
            dataset_version=context.dataset.version,
            inputs=inputs,
            epochs_run=epochs_run,
            stopped_early=stopped_early,
            best_epoch=best_epoch,
            history=history.history,
        )

    return run


def predictions(model: Any, features: Any, output: str) -> Any:
    """The model's raw output per sample: probabilities, a score, or a value."""
    return model.predict(features, verbose=0)[output]


def measure_split(
    output: dict[str, Any],
    raw: Any,
    targets: Any,
    *,
    split: str,
    dataset_version: str,
) -> tuple[list[dict[str, Any]], Any]:
    """The documented metrics of one split for the output's type, and a confusion matrix if any."""
    import numpy as np

    from caravan.metrics.classification import confusion_matrix, metrics_from_matrix
    from caravan.metrics.regression import regression_metrics
    from caravan.run.report import QualityMetric

    fitted = output["preprocessing"]["fitted"]
    if output["type"] == "number":
        values = regression_metrics(targets.tolist(), raw.reshape(-1).tolist())
        metrics = [
            QualityMetric(
                name=key,
                value=None if value is None else round(float(value), 6),
                split=split,
                dataset_version=dataset_version,
                samples=len(targets),
            ).as_dict()
            for key, value in values.items()
        ]
        return metrics, None
    if output["type"] == "category":
        labels = tuple(fitted["labels"])
        predicted = np.argmax(raw, axis=1)
        truth = targets
    else:
        labels = ("false", "true")
        predicted = (raw.reshape(-1) >= float(output.get("threshold", 0.5))).astype(np.int64)
        truth = targets.astype(np.int64)
    matrix = confusion_matrix(truth, predicted, len(labels))
    metrics, confusion = metrics_from_matrix(
        matrix, labels, split=split, dataset_version=dataset_version
    )
    return [metric.as_dict() for metric in metrics], confusion


def _write_measurements(
    out_dir: Path,
    *,
    model: Any,
    features: Any,
    targets: Any,
    split: Any,
    window_plan: Any,
    records: Any,
    output: dict[str, Any],
    dataset_version: str,
    inputs: StageInputs,
    epochs_run: int,
    stopped_early: bool,
    best_epoch: int,
    history: dict[str, Any],
) -> None:
    """Measure, then write the one artifact the report is built from.

    The report reads this file rather than the live objects, so a *reused* training result reports
    the same numbers as the run that produced it — which is what keeps FR-007 true on the reuse
    path as well as the first one.
    """
    measured: list[dict[str, Any]] = []
    matrices: dict[str, Any] = {}
    for name in ("val", "test"):
        indices = list(split.indices(name))
        raw = predictions(model, select(features, indices), output["name"])
        metrics, confusion = measure_split(
            output, raw, targets[indices], split=name, dataset_version=dataset_version
        )
        measured.extend(metrics)
        matrices[name] = confusion

    effective = {
        key.removeprefix("trainer."): value
        for key, value in inputs.items()
        if key.startswith("trainer.")
    }
    effective["random_seed"] = inputs["random_seed"]

    payload = {
        "dataset": {
            "records": records.schema.record_count,
            "feature_names": list(records.schema.feature_names),
            "ignored_columns": list(records.schema.ignored_names),
            "windows_kept": window_plan.samples,
            "windows_discarded_mixed": window_plan.discarded_mixed,
            "records_dropped_remainder": window_plan.dropped_remainder,
            "split": split.counts,
            "split_per_label": split.per_label_counts,
            # Feature 007: where the split came from, and what a fixed split threw away.
            "split_source": split.source,
            "windows_discarded_mixed_split": window_plan.discarded_mixed_split,
        },
        "training": {
            **framework_record(),
            "effective_settings": effective,
            "epochs_run": epochs_run,
            "stopped_early": stopped_early,
            "stopped_epoch": epochs_run if stopped_early else None,
            "best_epoch": best_epoch,
            "monitor": MONITOR,
            "finished": True,
        },
        "metrics": measured,
    }
    if matrices["test"] is not None:
        # The test split is the reference, so it is the matrix the report carries.
        payload["confusion_matrix"] = matrices["test"].as_dict()
    (out_dir / METRICS).write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / HISTORY).write_text(
        json.dumps(
            {key: [float(value) for value in values] for key, values in history.items()},
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
