# Contract: what the run reports and what the export states

**Feature**: 014-recording-aware-windows

## `data/schema.json` (data stage) — additions

```json
{
  "window": {"size": 64, "stride": 16, "label_rule": "last"},
  "recordings": [
    {"file": "a.csv", "key": null, "rows": 1000, "windows": 58, "leftover_rows": 8}
  ],
  "recordings_too_short": [],
  "windows_dropped": {"mixed": 3, "tied": 0, "mixed_split": 0, "purged": 6},
  "split": {
    "type": "recording", "derived": true, "seed": 42,
    "assignment": {"train": ["a.csv", "c.csv", "d.csv", "f.csv"], "val": ["b.csv"], "test": ["e.csv"]},
    "shares": {"train": 0.68, "val": 0.16, "test": 0.16},
    "counts": {"train": 160, "val": 38, "test": 37},
    "per_label": {"walk": {"train": 80, "val": 19, "test": 18}}
  }
}
```

The existing keys `windows_kept`, `windows_discarded_mixed`, `windows_discarded_mixed_split`,
`records_dropped_remainder`, `split_source` keep their names and meanings. For `blocked`, the
assignment lists blocks as `"<file>[<first row>:<end row>]"`.

## Console summary (stderr) — one block after the data stage

```text
data: 6 recordings, 5,412 rows → 235 windows of 64 rows, every 16 (label: last)
      dropped: 3 mixed, 6 at part boundaries · 40 leftover rows
split: by recording (derived: 6 recordings) — train 4 · val 1 · test 1 recordings
       shares 0.68 / 0.16 / 0.16 (asked 0.70 / 0.15 / 0.15)
```

With `random` or `stratify` and a window, the notice of `contracts/manifest-fields.md` follows.

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
