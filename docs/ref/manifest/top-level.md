# Top level

| Field | Type | Default |
|---|---|---|
| {mf}`apiVersion` | string | — required |
| {mf}`dataset` | string | — required |
| {mf}`random_seed` | integer | `42` |

:::{manifest-field} apiVersion
**Type** `string` · **Default** none — required · must be `caravan/v0.2` · read by **every stage**

**Does** — declares which schema the file is written in, so Caravan can refuse a file it would
otherwise misread.

**Default** — none, deliberately. A file without a version was once read as the oldest known
schema, and that guessed wrong silently; it is now an error ({rule}`V-1`).

**Change it** — only when migrating to a new schema. A manifest of the previous schema,
`caravan/v0.1`, is refused with a pointer to [the change notes](../manifest-changes.md), and each
key that moved is refused at its old path naming its new one.

**Extremes** — not applicable: one value is accepted.
:::

:::{manifest-field} dataset
**Type** `string` · **Default** none — required · a directory of `.csv`, `.tsv` or `.txt` files with a header row, or one such
file, relative to the manifest · read by **data**

**Does** — points at your data. Files in a directory are read in path order as one sequence of
records, oldest first, each with the same header row. An empty cell is a missing reading.

**Default** — none. There is nothing sensible to guess, and guessing would read the wrong data.

**Change it** — whenever the data moves. This is the one line that turns the worked example into
your own project.

**Extremes** — a directory whose files disagree on their header is refused; so is a file with no
header row. Your data is never copied into a run directory: Caravan reads it and records its
digest, so keeping it out of anything you publish stays your decision
({rule}`DS-1` to {rule}`DS-15`).
:::

:::{manifest-field} random_seed
**Type** `integer` · **Default** `42` · any · read by **data, build, train, quantize, export**

**Does** — fixes every random choice: the split, the weight initialisation, the shuffling, the
calibration sample. The same manifest and the same data give the same model.

**Default** — `42` is arbitrary and conventional. What matters is that there is one, so that a run
is reproducible without anybody having to think about it.

**Change it** — to find out how much of a result is the seed. Train the same manifest under three
seeds and you learn whether an accuracy figure is a property of your data or of one lucky draw.

**Extremes** — none in value, but note what it does *not* fix: a different framework version, or
different hardware, can still move the last decimal. The provenance of a number is in the run
report, not in the seed alone.
:::
