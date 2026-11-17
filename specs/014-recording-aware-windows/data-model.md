# Data Model: Windows That Know Their Recordings

**Feature**: 014-recording-aware-windows · **Date**: 2026-11-16

All of this lives in the core (`src/caravan/data/windows.py`, standard library only) except where a
reader field is named.

## Recording

A half-open range of global row indices `[start, end)`.

- Source: one per data file; additionally cut wherever `recording_column` changes value between
  consecutive rows.
- Carries: `file` (relative name), `key` (the recording column's value, or `None`), `rows`.
- Rule: windows never cross a recording's end (FR-001, FR-002).

`RecordSet` (reader) gains `recordings: tuple[Recording, ...]` and, when a `group` split names a
column, `groups: tuple[str, ...]` (that column's text per row), read like the fixed split's `parts`.

## WindowPlan (extended)

| Field | Type | New | Meaning |
|---|---|---|---|
| `window` | int \| None | | `window_size` |
| `stride` | int \| None | ✓ | `window_stride` |
| `rule` | str \| {"any": str} | ✓ | the window label rule applied |
| `kept` | tuple[int] | | first row of each kept window, in row order |
| `labels` | tuple[str] | | each kept window's label, per the rule |
| `recording_of` | tuple[int] | ✓ | index into `recordings` for each kept window |
| `dropped` | dict[str, int] | ✓ | counts by reason: `mixed`, `tied`, `mixed_split`, `purged` (filled by the split) |
| `per_recording` | tuple[dict] | ✓ | per recording: `file`, `key`, `rows`, `windows`, `leftover_rows` |
| `too_short` | tuple[int] | ✓ | recordings with fewer rows than one window |

`discarded_mixed`, `discarded_mixed_split` and `dropped_remainder` stay as derived properties, so the
existing report keys keep their meaning (remainder = sum of leftovers).

**Validation**: `1 ≤ stride ≤ window`; no window spans two recordings; with no kept window at all,
DS-6 as today, now naming the longest recording.

## SplitPlan (extended)

| Field | New | Meaning |
|---|---|---|
| `train`, `val`, `test` | | positions in `WindowPlan.kept` |
| `type` | ✓ | effective type: `random`, `stratify`, `fixed`, `recording`, `group`, `blocked` |
| `derived` | ✓ | true when the manifest left the type to the data (R5) |
| `seed` | | the seed actually used, after any retries (R4) |
| `assignment` | ✓ | for `recording`/`group`/`blocked`: `{part: [group keys or block ranges]}` |
| `shares` | ✓ | windows per part as reached, beside the stated probabilities |
| `per_label_counts` | | as today |
| `purged` | ✓ | windows dropped because they touched or overlapped another part |

**Invariants** (asserted by tests):
- every kept window is in exactly one part or counted as purged;
- for `recording`/`group`, all windows of one group are in one part;
- no row index belongs to windows of two different parts (FR-018);
- with a classification output, every part has every class, or the run was refused.

## Group

The unit a split assigns: a recording (`recording`), the set of rows sharing a value of
`split.column` (`group`), or a block of consecutive windows within one label stretch of one recording
(`blocked`). A group is never divided between parts.

## Window label rule

`all_equal | last | majority | mean | {any: value}` — see research R3 for results, drop reasons and
applicability per output type.

## State of a window

`candidate` (cut inside a recording) → `labelled` (rule gave a label) or `dropped: mixed | tied` →
`assigned: train | val | test` or `dropped: mixed_split | purged`.
