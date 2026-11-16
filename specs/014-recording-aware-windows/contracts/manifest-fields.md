# Contract: manifest fields (`caravan/v0.3`)

**Feature**: 014-recording-aware-windows

Only `preprocessing` changes. Every other section is as in `caravan/v0.2`.

```yaml
apiVersion: caravan/v0.3
preprocessing:
  window_size: 64
  window_stride: 16            # new; 1 … window_size; default window_size (no overlap)
  window_label: last           # new; all_equal | last | majority | mean | {any: <value>}
  recording_column: session    # new; optional; a change of value starts a new recording
  split:
    type: recording            # new values: recording | group | blocked (+ random, stratify, fixed)
    column: vehicle_id         # required by group (and fixed, as before)
    probabilities: [0.7, 0.15, 0.15]
```

## Defaults and resolution

| Field | Unset means | Shown by `render` | Recorded by a run |
|---|---|---|---|
| `window_stride` | `window_size` | the number | the number |
| `window_label` | `last` for `number`, `all_equal` otherwise | the rule | the rule |
| `recording_column` | none; each file is one recording | `null` | `null` |
| `split.type` with a window | chosen from the data: `recording` with ≥ 3 recordings, else `blocked` | `derived` | the effective type, with `derived: true` |
| `split.type` without a window | `random` | `random` | `random` |
| `split.probabilities` | `[0.7, 0.15, 0.15]`; for `recording`/`group`/`blocked` the *target* shares | the list | the list and the shares reached |

## Rules

| Rule | When |
|---|---|
| CF-20 | `window_stride` < 1 or > `window_size`, or set without `window_size` |
| CF-21 | `window_stride` < `window_size` with `random` or `stratify` |
| CF-22 | `window_label` not applicable to the output type (`mean` only for `number`; `majority`, `{any}` not for `number`); `window_label` or `recording_column` without a window |
| CF-23 | `recording_column` equals an input, the output or `split.column`; `group` without `split.column` |
| CF-13 | (unchanged) `stratify` names another column or a `number` output |
| DS-18 | `recording`/`group` with fewer groups than parts (3) |
| DS-19 | no assignment of groups gives every part every class |
| DS-20 | `{any: v}` and `v` never occurs in the output column; `recording_column` missing from a file |

Notice (not a finding, exit code unchanged): `random` or `stratify` with a window — "neighbouring
windows of one recording can fall into different parts and make the test score look better than the
model is; `recording`, `group` or `blocked` avoids this".

## Change note (`docs/ref/manifest-changes.md`, new section)

> **caravan/v0.2 → caravan/v0.3.** A manifest with `preprocessing.window_size` and no
> `preprocessing.split.type` used to split windows at random; it now splits by recording (three or
> more files, or recordings marked by `recording_column`) or in contiguous blocks. To keep the old
> behaviour, write `split: {type: random}` (or `stratify`). Windows no longer cross from one file to
> the next. New optional fields: `window_stride`, `window_label`, `recording_column`; new split types
> `recording`, `group`, `blocked`. Edit: change `apiVersion` to `caravan/v0.3`.
