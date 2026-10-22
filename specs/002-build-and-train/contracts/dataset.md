# Contract: The Dataset on Disk

Date: 2026-10-22 · Feature: 002 · Decisions: R4, R5, R6 in [research.md](../research.md)

This is the contract between Caravan and whoever brings the data. It is a convention the data must
meet, not a manifest field: the manifest gains nothing for it (Principle IX).

## What `dataset.source` points at

Raw, record-level delimited text — the data as it was recorded, not windows somebody prepared.

- A **file**: that file is the whole sequence.
- A **directory**: every file in it with a data extension (`.csv`, `.tsv`, `.txt`), in sorted
  relative-path order, read as one continuous sequence. Subdirectories are not searched at 0.1.0; a
  nested layout is a rejection naming what was found, never a partial read.

The reference is resolved relative to the manifest's own directory, so a manifest and its data move
together.

## The file

```csv
label,can_id,dlc,b0,b1,b2
normal,291,8,17,34,51
normal,608,8,18,36,54
dos,0,8,255,255,255
```

- A header row is required, in every file, and all files must agree on it.
- Exactly one column is named `label`. It holds the class name as it appears in `dataset.labels`.
- Every other column is a numeric feature, taken in header order. The order is part of the contract:
  it is the order the model sees, and it is recorded in the run report.
- The delimiter is a comma for `.csv`, a tab for `.tsv`, and a comma for `.txt`.
- No cell may be empty or non-numeric. There is no missing-value policy at 0.1.0, because inventing
  one silently is worse than refusing: a dataset with holes is the author's to fix, and the
  rejection names the file, the record and the column.

## From records to samples

With `dataset.window: w`, sample *i* is records `[i·w, (i+1)·w)` of the sequence. Windows do not
overlap — overlapping windows share records, so one can land in train and another in test, and the
test score stops meaning anything. Without a window, one record is one sample.

Three counts come out of this and all three go into the run report:

| Count | Meaning |
|---|---|
| `windows_kept` | samples the model will see |
| `windows_discarded_mixed` | windows whose records did not all carry the same label |
| `records_dropped_remainder` | records at the end that did not fill a window |

A discarded window is neither an error nor a silence. A window spanning the end of an attack burst
genuinely has two labels; majority voting has no answer for a tie, and "the last record's label"
mislabels every boundary. So it is dropped and counted, and the report says how many — the habit
Principle IV applies to a measurement, applied to a sample count.

If nothing is left, the run fails (DS-6) naming all three counts — and so does a dataset with fewer
records than one window, which is the same failure arriving earlier. "No usable data" never arrives
as a training run over zero samples.

What is *not* checked: the number of features. The manifest declares no feature width, so there is
nothing for the data to disagree with; the width is derived from the header and recorded. Two files
that disagree with each other about their columns are caught by DS-3.

## The split

Over samples, after the discard, never over records.

```text
for each label (or once over everything, when stratified is false):
    indices = sorted(indices with that label)
    random.Random(train.seed).shuffle(indices)
    n_train = floor(len(indices) * dataset.split.train)
    n_val   = floor(len(indices) * dataset.split.val)
    n_test  = floor(len(indices) * dataset.split.test)
    give the leftover to the split with the largest fraction; ties go to train
```

The standard library's `Random` is used, not the framework's, so the split is reproducible from the
report by anyone — including someone without the framework installed.

An empty part fails (DS-8) naming the part, the label and the counts. The manifest already forbids a
zero fraction, so an empty part means the data is too small for the manifest.

## The dataset version

`sha256` over, for each file in sorted relative-path order: its relative path, its byte length, and
its bytes. Nothing is parsed to compute it.

This is what the stage cache compares and what every metric records. It costs a full read of the
data per run — about a second per gigabyte — and that is the price of a cache that cannot be wrong
about whether the data changed. `dataset.source` is deliberately not part of a cache key: moving a
dataset must not retrain, changing it must.

## What Caravan does not claim about the data

It never verifies a licence or a permitted use. It holds the author to what they stated: a dataset
declared `benchmark-only` is never trained on (DS-9), and an unstated term is reported as unverified.
Responsibility for the rights to the data stays with whoever brings it — Principle VI as amended in
constitution v2.1.0.
