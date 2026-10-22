# Contract: Run Artifacts and the Report's New Sections

Date: 2026-10-22 · Feature: 002 · Extends [feature 001's run report contract](../../001-manifest-schema/contracts/run-report.md)

The run directory of feature 001 is unchanged in shape: one directory per invocation, never
overwritten, carrying the resolved manifest and the report. This document says what `build` and
`train` add to it, and what the report says about them.

## The run directory after `caravan train`

```text
runs/2026-10-22T17-05-02Z-cd34ef/
├── resolved-manifest.yaml       # from feature 001, unchanged
├── report.json                  # from feature 001, with the sections below added
├── model/
│   ├── built.keras              # the untrained model, as the builder constructed it
│   ├── built.json               # its shape, its layers and its parameter count
│   └── trained.keras            # the model after training
├── checkpoints/
│   ├── best.keras               # the best epoch by validation metric
│   └── final.keras              # the last epoch that ran
├── metrics.json                 # every quality metric, with what it was measured against
└── training-history.json        # per-epoch loss and metric values
```

After `caravan build`, only `model/built.keras` and `model/built.json` are present.

Rules:

- `built.json`, `metrics.json` and `training-history.json` are written with sorted keys and a
  trailing newline, so two runs diff readably.
- A run that failed, diverged to a non-finite loss, or was interrupted leaves **no** `trained.keras`
  and no `best.keras` (FR-012). What exists is the report, saying the run did not finish and at
  which epoch it stopped.
- Nothing is written outside the run directory and the cache directory. The dataset is read only.

## The report's new sections

Added to the document of feature 001, which keeps every field it had:

```json
{
  "command": "train",
  "stages": [ "...see the stage cache contract..." ],
  "dataset_resolved": {
    "root": "tests/fixtures/datasets/synthetic",
    "files": ["records.csv"],
    "version": "sha256:4f1c…",
    "total_bytes": 163840,
    "records": 5184,
    "feature_names": ["can_id", "dlc", "b0", "b1", "b2"],
    "windows_kept": 80,
    "windows_discarded_mixed": 1,
    "records_dropped_remainder": 0,
    "split": {"train": 56, "val": 12, "test": 12},
    "split_per_label": {"normal": {"train": 14, "val": 3, "test": 3}, "...": {}}
  },
  "training": {
    "framework": {"name": "tensorflow", "version": "2.21.0"},
    "keras_version": "3.15.1",
    "python": "3.13.16",
    "effective_settings": {
      "epochs": 50, "batch": 256, "optimizer": "adam", "learning_rate": 0.001,
      "early_stopping": true, "patience": 5, "seed": 42
    },
    "settings_from_default": ["learning_rate", "patience", "seed"],
    "epochs_run": 23,
    "stopped_early": true,
    "stopped_epoch": 23,
    "best_epoch": 18,
    "finished": true
  },
  "metrics": [
    {"name": "accuracy", "value": 0.9333, "split": "test",
     "dataset_version": "sha256:4f1c…", "samples": 12},
    {"name": "recall_per_class",
     "value": {"normal": 1.0, "dos": 0.75, "fuzzy": 1.0, "replay": 0.667},
     "split": "test", "dataset_version": "sha256:4f1c…", "samples": 12}
  ],
  "confusion_matrix": {
    "labels": ["normal", "dos", "fuzzy", "replay"],
    "split": "test",
    "dataset_version": "sha256:4f1c…",
    "rows": [[3, 0, 0, 0], [0, 3, 1, 0], [0, 0, 3, 0], [0, 1, 0, 2]]
  }
}
```

Rules that the writer enforces rather than documents:

- A metric is written only with `split`, `dataset_version` and `samples`. A metric missing any of
  them is a programming error and raises; it is never written without them (FR-007, SC-003). This is
  Principle IV's labelling habit applied to a quality number: a number that does not say what it was
  measured against is not a result.
- `settings_from_default` names which settings the author did not state, so FR-008's record is
  readable rather than merely complete.
- `framework` and its version appear in the report of any run that used it (FR-022). The provenance
  record includes the Python version, because which wheel ran is part of why a number came out as it
  did.
- `finished` is `false` for an interrupted or diverged run, and the metrics list is then empty rather
  than partial.

## What the next feature reads

The quantize stage of feature 003 reads `model/trained.keras` and, from the manifest,
`export.quantization`, `export.accuracy_drop_max` and `dataset.representative_samples`. It reads
nothing else from this run, which is what makes the stage boundary of the constitution's pipeline
contract real rather than nominal.
