# Research: Windows That Know Their Recordings

**Feature**: 014-recording-aware-windows · **Date**: 2026-11-16

Facts about the code were read at commit `f7bcace`. The measured failures come from the joint review
(`specs/013-guided-manifest-setup/review-2026-11-16.md`, findings A1–A4), which ran
`caravan.data.windows` on constructed inputs.

---

## R1. Where recordings come from, and how they reach the windowing

**Decision**: `read_records` (`src/caravan/data/reader.py:310`) keeps concatenating files into one
sequence — the arrays and the bridge stay as they are — but additionally returns `recordings`: a
tuple of half-open row ranges `[start, end)`, one per file, each further cut wherever the recording
column changes value between consecutive rows. `plan_windows` takes those ranges and cuts windows
inside each one, never across.

**Rationale**: every downstream consumer indexes rows by the global position (`plan.kept`,
`reader_bridge._window_rows`, `stages/data.training_rows`), so a global row index with recording
ranges beside it changes nothing for them. Cutting per file inside the reader would duplicate the
reader's header and cell checks. The recording column is read as text, the way the fixed split's
column already is (`_parts`), so no new parsing path appears.

**Alternatives considered**:
- *A list of per-file record sets*: cleaner in theory, but every stage and the bridge would change
  shape for no gain.
- *Insert a sentinel between files*: hides the boundary inside the data and breaks the row count the
  run report states.

---

## R2. The name and form of the new manifest fields

**Decision** (all under `preprocessing`, which is where the window already lives):

| Field | Form | Default |
|---|---|---|
| `recording_column` | a column name | none: each file is one recording |
| `window_label` | `all_equal` · `last` · `majority` · `mean` · `{any: <value>}` | `last` for a `number` output; `all_equal` otherwise |
| `window_stride` | integer, 1 … `window_size` | equal to `window_size` |
| `split.type` | `random` · `stratify` · `fixed` · `recording` · `group` · `blocked` | derived from the data when a window is set (R5); `random` otherwise |
| `split.column` | a column name | required by `group` and `fixed` |

**Rationale**: Ludwig has no names for these concepts, so Caravan's own plain words are used
(Principle I's naming practice of feature 008). `window_stride` rather than `training_stride` because
the manifest describes how the data is cut, and the field sits beside `window_size`; the interface
contract names it `training_stride` (R8), where the distinction from the device's step matters.
`{any: <value>}` as a one-key mapping keeps the value out of a string to be parsed and lets the
schema type the value like a label.

**Alternatives considered**: `sequence_column` (database jargon), `session_column` (too narrow for
vehicles and machines), `step` (ambiguous next to training epochs and "steps").

---

## R3. The window label rules, exactly

**Decision**: for a window's labels `l_1 … l_n` (oldest first):

| Rule | Result | Dropped as |
|---|---|---|
| `all_equal` | `l_1` if all equal | `mixed` otherwise (today's behaviour) |
| `last` | `l_n` | never |
| `majority` | the most frequent label | `tied` when two labels share the highest count |
| `mean` | the arithmetic mean of the values, written as the reader writes numbers | never; `number` outputs only |
| `{any: v}` | `v` if any `l_i == v` | otherwise as `all_equal` |

Applicability: `mean` only for `number`; `majority` and `{any}` not for `number`; `all_equal` and
`last` for every type. For `anomaly`, `{any: v}` with `v` the abnormal value makes a window with one
abnormal row abnormal, which the anomaly path then keeps out of training on normal windows.

**Rationale**: these are the rules the review named and practice uses (last row for state
estimation and online detection; any-of for intrusion and fault bursts; majority for activities with
noisy edges). Ties are dropped rather than broken arbitrarily, for the same reason today's code gives
(`windows.py:84-86`). For `{any}` the fallback is `all_equal`, not `last`, so a window of mixed
*other* labels is not silently assigned one.

---

## R4. Splits by group: the algorithm

**Decision**: `recording` and `group` both assign *groups* (a recording; or all rows sharing a value
of `split.column`) to parts:

1. Order the groups by their first row; shuffle with `random.Random(seed)` (the standard library's
   generator, as today).
2. Walk the shuffled groups; give each to the part whose share of windows is furthest below its
   target probability (ties: train, val, test).
3. For a classification output, check that every part has every class. If not, retry from step 1
   with seeds `seed+1 … seed+99`; the first assignment that satisfies the check wins and its seed is
   recorded. If none does, refuse (DS-19) with the per-class window counts per group.
4. Fewer groups than parts: refuse (DS-18) naming the counts and `blocked` as the alternative.

**Rationale**: greedy-by-deficit is reproducible from the report and close to GroupShuffleSplit
without a dependency (Principle XII); retrying seeds is the cheapest honest way to "try" class
coverage (FR-013) and is fully recorded. Groups are never split, which is the point.

**Alternatives considered**: an exact bin-packing solver (overkill, opaque in a report); stratified
group k-fold (needs folds Caravan does not have).

---

## R5. The blocked split, and the default

**Decision**: `blocked` cuts each recording's kept windows into contiguous blocks and assigns blocks
to parts:

- For a classification output, blocks are formed **within each stretch of one label**, so each class
  contributes blocks; blocks are assigned per class by the same seeded deficit walk, which makes the
  split stratified by construction.
- Block size: `max(1, round(windows_in_stretch / 10))` windows, so a stretch yields about ten blocks
  and three parts can be reached even for a short stretch; documented, not a manifest field.
- After assignment, **purging**: walking each recording in order, a window whose rows touch or overlap
  the rows of the previous kept window of a *different* part is dropped and counted as `purged`
  (FR-010, FR-018). With `window_stride == window_size` this leaves a gap of exactly one window at
  each change of part.

**Default** (FR-011): when `window_size` is set and `split.type` is not stated, the run derives
`recording` if the data has at least three recordings, otherwise `blocked`. The resolved manifest of
`render` shows `type: derived`; the run's resolved manifest shows the effective type (Principle I:
"the value a run derived MUST be recorded").

**Rationale**: the review's two-class example under `blocked`: no test window has a training window
directly beside it, because the purge removes exactly those (SC-004 asks for at most one in ten).
Ten blocks per stretch keeps the part shares close to the probabilities.

**Alternatives considered**: one block per part (three contiguous thirds) — a class confined to one
third would be missing from the others; random blocks of a fixed number of rows — blocks would cross
label stretches and lose stratification.

---

## R6. Overlapping windows

**Decision**: within each recording, windows start at `r_start + k * window_stride` while the window
fits. `window_stride < window_size` is refused (CF-21) with `random` and `stratify`, allowed with
`recording`, `group`, `blocked`, `fixed` and the derived default. The purge of R5 applies to every
split type, so no row is shared across parts (FR-018); for `recording`/`group` it never triggers,
because groups do not share rows.

**Rationale**: overlap is safe once the split assigns groups, and it is how sensor and keyword models
gain examples and robustness to offsets (review §3.4). The purge makes the guarantee unconditional
rather than dependent on the split type.

---

## R7. Validation rules and their identifiers

**Decision**: new rules, numbered after the existing ones (`src/caravan/manifest/errors.py`):

| Rule | Checked by | Refuses |
|---|---|---|
| CF-20 | validate | `window_stride`, `window_label` or `recording_column` set without a window; `window_stride` outside 1 … `window_size` |
| CF-21 | validate | `window_stride < window_size` with `random` or `stratify` |
| CF-22 | validate | a `window_label` that does not apply to the output type |
| CF-23 | validate | `recording_column` that is an input, the output or the split column; `group` without `split.column` |
| DS-18 | data | fewer groups than parts for `recording`/`group` |
| DS-19 | data | no assignment gives every part every class: for `recording`/`group` after the retries of R4; for `blocked` when a class's stretches yield fewer blocks than parts |
| DS-20 | data | `{any: v}` where the output column never contains `v`; the recording column missing from a file |

A random or stratified split with a window is accepted with a notice (FR-012), printed by `validate`
and recorded in the report; notices are not findings and do not change the exit code.

---

## R8. The interface contract

**Decision**: `contract_version` 3 → 4. `"stride"` is renamed `"training_stride"` and carries
`window_stride`; a new `"window_label"` carries the rule (`"all_equal"`, `"last"`, … or
`{"any": "<value>"}`); a one-line `"training_stride_note"` states that it describes how the training
data was cut and that a firmware may read with any step. Nothing else in the contract changes.

**Rationale**: FR-019; the review's firmware developer showed `"stride": window_size`
(`export/interface.py:139`) reads as a device requirement. The device-side fields (sample period,
recommended inference step, warm-up) belong to package P3 and are deliberately not added here.

---

## R9. The schema version and the change note

**Decision**: `caravan/v0.2` → `caravan/v0.3`. The change is breaking under the procedure in
`docs/ref/manifest-changes.md` ("a changed meaning"): a windowed manifest without a split used to mean
`random` and now means a split by recording or block. The change note says so and gives the edit that
restores the old behaviour (`split: {type: random}`, or `stratify`). All 39 manifests in the
repository are rewritten to `caravan/v0.3`; those that relied on the old default get no edit — their
new behaviour is the intended fix — except where a test asserts on a random split, which states it.

---

## R10. Fixtures

**Decision**: three new generated datasets under `tests/fixtures/datasets/`, each with its
`make.py`, small enough for the core test matrix:

| Fixture | Shape | Proves |
|---|---|---|
| `recordings/` | 6 files, two classes, lengths not multiples of the window | per-file windows, leftovers per file, `recording` split, overlap and purge |
| `soc/` | 2 files, a `number` target falling 0.01 per row | `last` and `mean` yield windows (SC-001) |
| `bursts/` | 1 file, `normal` with 20-row `dos` bursts every 200 rows | `{any: dos}` keeps the burst class (SC-002); `blocked` default |

A test reproduces the review's leakage example (two classes in contiguous 3,200-row blocks, window 64,
seed 42) and asserts SC-004.
