"""The train stage: the model, the data, and the numbers that describe the result.

Core module — every framework import is inside a function, so importing it loads no framework.

Two things here are the feature's honesty, not its mechanics. The run refuses to train on data the
author marked as not permitted for training (DS-9): their own statement, enforced against them,
which is the whole of what Principle VI claims. And a diverged run leaves nothing behind (DS-10,
FR-012) — no trained model, no best checkpoint — because the stage writes into a private directory
that is only published if it finishes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from caravan.data.windows import SPLIT_NAMES, plan_split, plan_windows
from caravan.manifest.errors import (
    RULE_TRAINING_DIVERGED,
    RULE_TRAINING_NOT_PERMITTED,
    run_rule_error,
)
from caravan.stages._framework import framework_record
from caravan.stages.base import StageContext, StageFunction, StageInputs, StageSpec
from caravan.stages.build import load_built_model, require_framework

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
    # tuple. ``dataset.window`` and ``dataset.labels`` are here because forming samples and
    # ordering the output units needs them; the plan had left them to the build stage, and the
    # projection is what made that visible.
    reads=(
        "train.epochs",
        "train.batch",
        "train.optimizer",
        "train.learning_rate",
        "train.early_stopping",
        "train.patience",
        "train.seed",
        "dataset.split",
        "dataset.labels",
        "dataset.window",
        "dataset.permitted_use",
    ),
    reads_dataset=True,
    upstream="build",
    artifacts=(TRAINED_MODEL, BEST_CHECKPOINT, FINAL_CHECKPOINT, METRICS, HISTORY),
)

#: The one stated use that forbids training. ``unknown`` does not: an unstated term is reported as
#: unverified (feature 001, FR-032), not treated as a prohibition the author did not write.
BENCHMARK_ONLY = "benchmark-only"


class Diverged(Exception):
    """Raised from inside the training loop when the loss stops being a number."""

    def __init__(self, epoch: int, value: object) -> None:
        super().__init__(f"the loss became {value} at epoch {epoch}")
        self.epoch = epoch
        self.value = value


def check_permitted(permitted_use: str) -> None:
    """DS-9: the author's own statement about their data, kept.

    Caravan never verifies a licence. What it does is hold an author to what they wrote: a dataset
    declared ``benchmark-only`` is never trained on, and the message names the field rather than
    interpreting any terms.
    """
    if permitted_use == BENCHMARK_ONLY:
        run_rule_error(
            RULE_TRAINING_NOT_PERMITTED,
            "dataset.permitted_use",
            (
                "the manifest states that this dataset is permitted for benchmarking only, so it "
                "must not be trained on; nothing was trained"
            ),
            found=permitted_use,
            accepted=("training", "unknown"),
        )


def _optimizer(name: str, learning_rate: float) -> Any:
    import keras

    builders = {
        "adam": keras.optimizers.Adam,
        "adamw": keras.optimizers.AdamW,
        "sgd": keras.optimizers.SGD,
    }
    return builders[name](learning_rate=learning_rate)


def _samples(records: Any, plan: Any, labels: tuple[str, ...]) -> tuple[Any, Any]:
    """Stack the planned windows into one array, and the labels into class indices."""
    import numpy as np

    index_of = {label: position for position, label in enumerate(labels)}
    if plan.window is None:
        features = records.features
    else:
        features = np.stack([records.features[start : start + plan.window] for start in plan.kept])
    targets = np.array([index_of[label] for label in plan.labels], dtype=np.int64)
    return features, targets


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


def stage(context: StageContext) -> StageFunction:
    """The stage function, bound to this run's dataset."""

    def run(inputs: StageInputs, out_dir: Path) -> None:
        require_framework("train")
        check_permitted(inputs["dataset.permitted_use"])

        import keras

        labels = tuple(inputs["dataset.labels"])
        seed = int(inputs["train.seed"])
        keras.utils.set_random_seed(seed)

        records = context.records()
        window_plan = plan_windows(records.labels, inputs["dataset.window"])
        split_spec = inputs["dataset.split"]
        split = plan_split(
            window_plan,
            {name: float(split_spec[name]) for name in SPLIT_NAMES},
            stratified=bool(split_spec["stratified"]),
            seed=seed,
            labels=labels,
        )
        features, targets = _samples(records, window_plan, labels)

        # The build stage's artifacts are already in the run directory, whether this run
        # produced them or reused them from the cache.
        model = load_built_model(context.run_dir)
        model.compile(
            optimizer=_optimizer(inputs["train.optimizer"], float(inputs["train.learning_rate"])),
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
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
        if bool(inputs["train.early_stopping"]):
            callbacks.append(
                keras.callbacks.EarlyStopping(
                    monitor=MONITOR,
                    patience=int(inputs["train.patience"]),
                    restore_best_weights=True,
                )
            )

        try:
            history = model.fit(
                features[list(split.train)],
                targets[list(split.train)],
                validation_data=(features[list(split.val)], targets[list(split.val)]),
                epochs=int(inputs["train.epochs"]),
                batch_size=int(inputs["train.batch"]),
                callbacks=callbacks,
                shuffle=True,
                verbose=0,
            )
        except Diverged as diverged:
            run_rule_error(
                RULE_TRAINING_DIVERGED,
                "train.learning_rate",
                (
                    f"training diverged: {diverged}. No model was written. A learning rate this "
                    "size, or data that is not scaled, is where to look"
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
        stopped_early = epochs_run < int(inputs["train.epochs"])

        _write_measurements(
            out_dir,
            model=model,
            features=features,
            targets=targets,
            split=split,
            window_plan=window_plan,
            records=records,
            labels=labels,
            dataset_version=context.dataset.version,
            inputs=inputs,
            epochs_run=epochs_run,
            stopped_early=stopped_early,
            best_epoch=best_epoch,
            history=history.history,
        )

    return run


def _write_measurements(
    out_dir: Path,
    *,
    model: Any,
    features: Any,
    targets: Any,
    split: Any,
    window_plan: Any,
    records: Any,
    labels: tuple[str, ...],
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
    import numpy as np

    from caravan.metrics.classification import confusion_matrix, metrics_from_matrix

    measured: list[dict[str, Any]] = []
    matrices: dict[str, Any] = {}
    for name in ("val", "test"):
        indices = list(split.indices(name))
        probabilities = model.predict(features[indices], verbose=0)
        predicted = np.argmax(probabilities, axis=1)
        matrix = confusion_matrix(targets[indices], predicted, len(labels))
        metrics, confusion = metrics_from_matrix(
            matrix, labels, split=name, dataset_version=dataset_version
        )
        measured.extend(metric.as_dict() for metric in metrics)
        matrices[name] = confusion

    effective = {
        key.removeprefix("train."): value
        for key, value in inputs.items()
        if key.startswith("train.")
    }

    payload = {
        "dataset": {
            "records": records.schema.record_count,
            "feature_names": list(records.schema.feature_names),
            "windows_kept": window_plan.samples,
            "windows_discarded_mixed": window_plan.discarded_mixed,
            "records_dropped_remainder": window_plan.dropped_remainder,
            "split": split.counts,
            "split_per_label": split.per_label_counts,
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
        # The test split is the reference, so it is the matrix the report carries.
        "confusion_matrix": matrices["test"].as_dict(),
    }
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
