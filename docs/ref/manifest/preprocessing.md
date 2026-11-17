# The `preprocessing` section

| Field | Type | Default |
|---|---|---|
| {mf}`preprocessing.window_size` | integer | — required by every template |
| {mf}`preprocessing.window_stride` | integer | the window size: no overlap |
| {mf}`preprocessing.window_label` | string or `{any: <value>}` | `last` for a number, `all_equal` otherwise |
| {mf}`preprocessing.window_label.any` | a label | — only in `{any: <value>}` |
| {mf}`preprocessing.recording_column` | string | none: each file is one recording |
| {mf}`preprocessing.split.type` | string | with a window: chosen from the data; else `random` |
| {mf}`preprocessing.split.probabilities` | list of three numbers | `[0.7, 0.15, 0.15]` |
| {mf}`preprocessing.split.column` | string | the output's column, for `stratify` |

:::{manifest-field} preprocessing.window_size
**Type** `integer` · **Default** none — required by templates that consume a window, which all four
do; left out with an image input ({rule}`CF-19`) · at least 1 · read by **every stage**

**Does** — how many consecutive records of one recording form one sample. A window never reaches
from one recording into the next ({mf}`preprocessing.recording_column`); how often a new one starts
is {mf}`preprocessing.window_stride`, and what label it carries is
{mf}`preprocessing.window_label`.

**Default** — none. It comes from your physics, not from the model: how many time steps it takes to
see the thing you want to recognise.

**Change it** — when the phenomenon is longer or shorter than you thought. Without overlap this
also sets how many samples you have: half the window gives twice the samples, less any windows
discarded for a change of label.

**Extremes** — too long and you have few samples and mixed windows get discarded; too short and the
pattern does not fit inside one. Under the default label rule, a window longer than your shortest
labelled stretch produces no usable samples for that class at all; a recording shorter than the
window gives none and is named in the report ({rule}`CF-6`, {rule}`DS-6`).
:::

:::{manifest-field} preprocessing.window_stride
**Type** `integer` · **Default** the window size · 1 to the window size · read by **data, train,
quantize, export**

**Does** — how many records apart two windows start within one recording. At the window size,
windows sit side by side; smaller, they overlap.

**Default** — the window size: no overlap, so no two windows share a record.

**Change it** — smaller when you have little data: a quarter of the window gives about four times
the windows, and teaches the model windows that start part-way into an event, as a device that
predicts more often will feed it. It is how the training data is cut, not how the device must
read: the export's interface contract says so beside it (`training_stride`).

**Extremes** — overlapping windows share records, so a split that places windows one by one could
put the same record in training and in test; overlap is only accepted with a split by recording,
group or block, or a fixed split ({rule}`CF-20`, {rule}`CF-21`).
:::

:::{manifest-field} preprocessing.window_label
**Type** `string` or `{any: <value>}` · **Default** `last` for a `number` output, `all_equal` otherwise ·
`all_equal`, `last`, `majority`, `mean` (numbers only) or `{any: <value>}` (not for numbers) · read
by **data, train, quantize, export**

**Does** — how a window's records' labels become the window's label. `all_equal` keeps a window only
when its records agree; `last` takes the newest record's label; `majority` the most frequent, and
drops a tie; `mean` averages a number; `{any: dos}` labels a window `dos` when any of its records is
`dos`, and otherwise behaves as `all_equal`.

**Default** — `all_equal` for classes, so a window never gets a label it cannot be known to have;
`last` for a number, which almost never stays exactly equal across a window (state of charge,
temperature).

**Change it** — `{any: <value>}` when the thing to detect is short and rare, such as an attack burst
between normal frames or a fault that lasts a few readings: under `all_equal` every window around
it is mixed and dropped, and the class vanishes. `last` when a prediction is about the newest moment.

**Extremes** — `mean` on a class or `majority` on a number has no meaning and is refused; a value in
`{any: …}` the output column never holds is refused when the data is read. The export's interface
contract carries the rule, so the firmware knows what a prediction means ({rule}`CF-22`,
{rule}`DS-20`).
:::

:::{manifest-field} preprocessing.window_label.any
**Type** a label, as the output column spells it · **Default** none · only inside
`window_label: {any: <value>}` · read by **data, train, quantize, export**

**Does** — the label a window takes when any of its records carries it.

**Default** — none; the rule exists only with a value.

**Change it** — to the rare, short class you need to detect: `dos`, `fault`, `arc`.

**Extremes** — a value the column never holds is refused with the values it does hold
({rule}`DS-20`).
:::

:::{manifest-field} preprocessing.recording_column
**Type** `string` · **Default** none: each file is one recording · a column of the data · read by
**data, train, quantize, export**

**Does** — names a column that marks recordings inside a file: wherever its value changes from one
record to the next, a new recording begins, and no window reaches across. Every file is a recording
of its own anyway.

**Default** — none. One file per session, trip or test run is the simplest way to say where
recordings end.

**Change it** — when several sessions share one file: a `session`, `trip` or `run` column.

**Extremes** — the column is never read by the model, so it cannot also be an input, the output or
the split column; a file without it is refused ({rule}`CF-23`, {rule}`DS-20`).
:::

:::{manifest-field} preprocessing.split.type
**Type** `string` · **Default** with a window, chosen from the data (`recording` or `blocked`); without
one, `random` · `recording`, `group`, `blocked`, `random`, `stratify` or `fixed` · read by **data,
train, quantize, export**

**Does** — decides how windows become training, validation and test parts. `recording` keeps every
recording's windows in one part; `group` every value of {mf}`preprocessing.split.column`; `blocked`
cuts each stretch of one label into contiguous blocks and leaves out the windows that would touch a
block of another part. `random` and `stratify` place windows one by one by `probabilities`, `stratify`
per class; `fixed` lets a column of your data name each record's part.

**Default** — with a window, the run chooses: `recording` when at least three recordings yield
windows, `blocked` otherwise, and records what it chose (`render` shows `derived`). Neighbouring
windows of one recording are near-copies, and a split that places them one by one tests the model on
copies of its training data; the default never does.

**Change it** — `group` when windows from one subject, vehicle or machine must stay together across
files; `fixed` when you have decided the parts yourself. `random` or `stratify` are still accepted,
with a notice that neighbouring windows can fall into different parts and make the test score look
better than the model is.

**Extremes** — too few recordings or groups for three parts, or a class held by too few of them,
is refused with the counts; a blocked split needs every class in at least three blocks
({rule}`CF-12`, {rule}`CF-15`, {rule}`DS-18`, {rule}`DS-19`).
:::

:::{manifest-field} preprocessing.split.probabilities
**Type** `list of three numbers` · **Default** `[0.7, 0.15, 0.15]` · train, validation, test; each above 0,
summing to 1; not allowed with `fixed` · read by **data, train, quantize, export**

**Does** — the shares of the three parts. A split by recording, group or block assigns whole groups,
so these are targets; the report states the shares actually reached.

**Default** — `[0.7, 0.15, 0.15]`, the usual compromise between having enough to learn from and
enough to measure on.

**Change it** — give the test part more when a metric needs to mean something on a small dataset,
and less when there is barely enough to train.

**Extremes** — a tiny test part makes accuracy jump in large steps: with 12 test windows, one
changed prediction moves accuracy by 8 points, which is larger than a typical quantization budget.
The run report states the resolution for exactly this reason
({rule}`CF-1`, {rule}`DS-8`).
:::

:::{manifest-field} preprocessing.split.column
**Type** `string` · **Default** the output's column for `stratify` · for `stratify`, the output's column; for
`group`, the column to keep together; for `fixed`, the column naming each record's part · read by
**data, train, quantize, export**

**Does** — with `stratify`, the column whose classes are balanced across parts. With `group`, the
column whose values each stay in one part (a subject, a vehicle, a machine). With `fixed`, the
column in which every record names its part, as `train`, `validation` or `test`, or as Ludwig's
`0`, `1`, `2`.

**Default** — the output's column, which is what stratifying almost always means.

**Change it** — with `fixed`, to whichever column you added for the purpose.

**Extremes** — a window whose records name two different parts or groups is discarded. The split
column is never a feature, so it cannot leak into the model
({rule}`CF-13`, {rule}`DS-13`).
:::
