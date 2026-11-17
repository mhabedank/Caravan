# Contract: what the run reports and what the export states

**Feature**: 014-recording-aware-windows

## `data/schema.json` (data stage) — additions

```json
{
  "window": {"size": 32, "stride": 8, "label_rule": "all_equal"},
  "recordings": [
    {"file": "r1.csv", "key": null, "rows": 450, "windows": 48, "leftover_rows": 2}
  ],
  "recordings_too_short": [],
  "windows_dropped": {"mixed": 81, "tied": 0, "mixed_split": 0, "purged": 0},
  "split": {"train": 205, "val": 50, "test": 38},
  "split_plan": {
    "type": "recording", "derived": true, "seed": 42,
    "assignment": {"train": ["r1.csv", "r3.csv", "r5.csv", "r6.csv"], "val": ["r2.csv"], "test": ["r4.csv"]},
    "shares": {"train": 0.6997, "val": 0.1706, "test": 0.1297}
  }
}
```

(Figures from the end-to-end run on `tests/fixtures/manifests/valid/recordings-conv1d.yaml`.) As
built, `split` keeps its earlier meaning — the count of windows per part, which earlier readers use —
and the new detail sits in `split_plan` beside it rather than inside it. `split_per_label` (train
stage) keeps the per-class counts.

The existing keys `windows_kept`, `windows_discarded_mixed`, `windows_discarded_mixed_split`,
`records_dropped_remainder`, `split_source` keep their names and meanings. For `blocked`, the
assignment lists blocks as `"<file>[<first row>:<end row>]"`.

## Console summary (stderr) — one line after the data line

```text
windows: 293 of 32 rows, every 8 (label: all_equal), from 6 recordings; split by recording (derived: 6 recordings), shares 0.70 / 0.17 / 0.13; left out: 81 mixed
```

With `random` or `stratify` and a window, the notice of `contracts/manifest-fields.md` is printed
before the stages run.

## `model/interface.json` — contract version 4

```json
{
  "contract_version": 4,
  "window_size": 64,
  "training_stride": 16,
  "training_stride_note": "how the training data was cut; a firmware may read with any step",
  "window_label": "last"
}
```

`"stride"` is removed (renamed). No other key changes.
