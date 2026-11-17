# Quickstart: validating windows that know their recordings

**Feature**: 014-recording-aware-windows

Each step names the requirement or criterion it proves. Field forms are in
[contracts/manifest-fields.md](contracts/manifest-fields.md); report shapes in
[contracts/reports.md](contracts/reports.md).

## Prerequisites

The core suite runs on a default installation (windowing and splitting import no framework,
FR-020). Steps 6–7 need the `train` extra on Python 3.13.

```bash
pip install -e ".[train,verify]"
```

## 1. No window crosses a file (US1, FR-001, SC-003)

```bash
pytest tests/unit/test_windows_recordings.py -q
```

Expected: on `tests/fixtures/datasets/recordings/` (six files, lengths not multiples of the window),
every window lies inside one file, each file's first window starts at its first row, and the report
lists each file's leftover rows.

## 2. The default split does not leak (US2, FR-011, SC-004)

```bash
pytest tests/unit/test_split_groups.py -q
```

Expected: the review's example (two classes in contiguous 3,200-row blocks, one file, window 64,
seed 42) resolves to `blocked`, and no test window has a training window directly beside it (today
13 of 15); the six-file fixture resolves to `recording`, and every file's windows are in one part.

## 3. Too few recordings, and a class in one stretch only (US2 scenarios 3 and 6, DS-18, DS-19)

```bash
pytest tests/contract/test_split_refusals.py -q
```

Expected: two files with `split: {type: recording}` → DS-18 naming 2 recordings, 3 parts and
`blocked`; a class confined to one group → DS-19 with per-class counts.

## 4. Every output gets windows (US3, FR-005–FR-007, SC-001, SC-002)

```bash
pytest tests/unit/test_window_label.py -q
```

Expected: `soc/` (number falling 0.01 per row) yields ≥ 90% of possible windows with the default
`last`; `bursts/` keeps ≥ 1 `dos` window per burst with `window_label: {any: dos}` and window 64;
`majority` drops ties and counts them; `{any: nope}` refuses with DS-20 and the values present.

## 5. Overlap, safely (US4, FR-016–FR-018, SC-005)

```bash
pytest tests/unit/test_window_stride.py tests/contract/test_manifest_v03.py -q
```

Expected: stride 16 on window 64 gives ≥ 3.5× the windows; no row index belongs to windows of two
parts; stride 16 with `split: {type: random}` is refused (CF-21); stride 65 is refused (CF-20).

## 6. The manifest and its notice (FR-012, FR-021)

```bash
caravan validate examples/picket-mlp.yaml --no-report
caravan render examples/picket-mlp.yaml --stdout | grep -A4 'split:'
```

Expected: valid under `caravan/v0.3`; the rendered split shows the example's stated type; a copy with
`split: {type: random}` validates and prints the neighbouring-windows notice; a `caravan/v0.2`
manifest is refused with V-1 pointing to the change note.

## 7. End to end, and the contract (FR-014, FR-019)

```bash
caravan export tests/fixtures/manifests/valid/recordings-conv1d.yaml
```

Expected: the console shows the data block of `contracts/reports.md`; `data/schema.json` lists
recordings, drops by reason and the split assignment; `model/interface.json` has `contract_version`
4, `training_stride` and `window_label`, and no `stride`.

## 8. Everything else still holds

```bash
pytest -q
pytest tests/layering -q
```
