# The `preprocessing` section

| Field | Type | Default |
|---|---|---|
| {mf}`preprocessing.window_size` | integer | — required by both templates |
| {mf}`preprocessing.split.type` | string | `random` |
| {mf}`preprocessing.split.probabilities` | list of three numbers | `[0.7, 0.15, 0.15]` |
| {mf}`preprocessing.split.column` | string | the output's column, for `stratify` |

:::{manifest-field} preprocessing.window_size
**Type** `integer` · **Default** none — required by templates that consume a window, which both do · at least 1 · read by
**every stage**

**Does** — how many consecutive records form one sample. Windows never overlap, and a window whose
records disagree about the output is discarded and counted.

**Default** — none. It comes from your physics, not from the model: how many time steps it takes to
see the thing you want to recognise.

**Change it** — when the phenomenon is longer or shorter than you thought. Because windows do not
overlap, this also sets how many samples you have: half the window gives twice the samples, less any
windows discarded for a change of label.

**Extremes** — too long and you have few samples and mixed windows get discarded; too short and the
pattern does not fit inside one. A window longer than your shortest labelled stretch produces no
usable samples for that class at all ({rule}`CF-6`,
{rule}`DS-6`).
:::

:::{manifest-field} preprocessing.split.type
**Type** `string` · **Default** `random` · `random`, `stratify` or `fixed` · read by **data, train, quantize,
export**

**Does** — decides how windows become training, validation and test parts. `random` splits by
`probabilities`; `stratify` does so per class, keeping the shares equal; `fixed` lets a column of
your data name each record's part.

**Default** — `random`, the simplest thing that works on balanced data.

**Change it** — `stratify` when classes are uneven, so that a rare class is present in every part.
**`fixed` when windows from one subject, vehicle, session or recording must not land on both
sides** — and also when your recording was cut into overlapping pieces before Caravan saw it.

**Extremes** — `random` on data with near-duplicate windows is the classic way to get a test score
that is too good: the test part holds near-copies of training data, every number looks excellent,
and the board disappoints. That failure has no symptom inside Caravan, which is why `fixed` exists
({rule}`CF-12`, {rule}`CF-15`).
:::

:::{manifest-field} preprocessing.split.probabilities
**Type** `list of three numbers` · **Default** `[0.7, 0.15, 0.15]` · train, validation, test; each above 0,
summing to 1; not allowed with `fixed` · read by **data, train, quantize, export**

**Does** — the shares of the three parts.

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
`fixed`, the column naming each record's part · read by **data, train, quantize, export**

**Does** — with `stratify`, the column whose classes are balanced across parts. With `fixed`, the
column in which every record names its part, as `train`, `validation` or `test`, or as Ludwig's
`0`, `1`, `2`.

**Default** — the output's column, which is what stratifying almost always means.

**Change it** — with `fixed`, to whichever column you added for the purpose.

**Extremes** — a window whose records name two different parts is discarded. The split column is
never a feature, so it cannot leak into the model
({rule}`CF-13`, {rule}`DS-13`).
:::
