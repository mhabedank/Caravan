# The `output_features` section

Exactly one entry: the column the model answers ({rule}`CF-17`).

| Field | Type | Default |
|---|---|---|
| {mf}`output_features[].name` | string | — required |
| {mf}`output_features[].type` | string | — required |
| {mf}`output_features[].preprocessing.vocab` | list | `derived` |
| {mf}`output_features[].preprocessing.fallback_true_label` | string | none |
| {mf}`output_features[].preprocessing.normal_label` | string | `normal` (anomaly) |
| {mf}`output_features[].preprocessing.normalization` | string or null | `null` |
| {mf}`output_features[].loss.type` | string | `mean_squared_error` (number) |
| {mf}`output_features[].loss.class_weights` | list or mapping | none |
| {mf}`output_features[].loss.positive_class_weight` | number | none |
| {mf}`output_features[].threshold` | number | `0.5` (binary) |
| {mf}`output_features[].clip` | list of two numbers | none |
| {mf}`output_features[].accuracy_drop_max` | number | — required for category and binary |
| {mf}`output_features[].mae_increase_max` | number | — required for number |
| {mf}`output_features[].auc_drop_max` | number | — required for anomaly |
| {mf}`output_features[].threshold_percentile` | number | `95` (anomaly) |

:::{manifest-field} output_features[].name
**Type** `string` · **Default** none — required · a column of the data · read by **every stage**

**Does** — names the column the model answers.

**Default** — none.

**Change it** — when you are predicting something else.

**Extremes** — a name that is also an input feature is refused ({rule}`CF-11`); so is one
that is not a column of the data ({rule}`CF-9`).
:::

:::{manifest-field} output_features[].type
**Type** `string` · **Default** none — required · `category`, `binary`, `number` or `anomaly` · read
by **every stage**

**Does** — decides what the model learns to produce, which budget field applies, and how an answer
is turned into a decision: a category takes the argmax, a binary compares with `threshold`, a number
is the value itself, and an anomaly score is abnormal at or above its threshold.

**`anomaly`** names the column that tells normal from abnormal; every value other than
{mf}`normal_label <output_features[].preprocessing.normal_label>` is abnormal. The model's output
is the **anomaly score**: the mean squared difference between the window as the model saw it and its
reconstruction, computed inside the model. Training learns from the normal windows of the training
part only; calibration uses all of them. The threshold is the
{mf}`threshold_percentile <output_features[].threshold_percentile>`-th percentile of the int8
model's scores on the validation part's normal windows. `quantization.json` records it, with the
detection and false alarm rates on the test part, and `interface.json` states it. Only the
`autoencoder` template answers it ({rule}`CF-18`).

**Default** — none.

**Change it** — when the question changes. Two classes can be modelled either way; `binary` is the
smaller model and gives you a threshold to tune, `category` generalises to more classes later.

**Extremes** — `number` on something that is really a set of labels produces answers between the
labels, which mean nothing ({rule}`CF-14`).
:::

:::{manifest-field} output_features[].preprocessing.vocab
**Type** `list` · **Default** `derived`: by frequency in the training part · every class of the data, in your
order · `category` only · read by **data**

**Does** — pins the class order, which is the order of the scores the model outputs and the order
of the labels in the exported header.

**Default** — `derived`, by frequency in the training part.

**Change it** — when your firmware has the old label order compiled into it. Pinning here is how a
retrained model stays compatible with a deployed board.

**Extremes** — a class present in the data but missing from a pinned vocabulary is an error, not a
silent drop ({rule}`DS-5`, {rule}`DS-11`, {rule}`DS-14`).
:::

:::{manifest-field} output_features[].preprocessing.fallback_true_label
**Type** `string` · **Default** none · `binary` only · read by **data**

**Does** — as for an input feature: which of two spellings means true.

**Default** — none, and the value that sorts second becomes true.

**Change it** — for any pair Caravan does not recognise. On the output this matters more than on an
input, because it decides what your model's "yes" means ({rule}`DS-15`).

**Extremes** — getting it wrong inverts every answer while every metric still looks plausible.
:::

:::{manifest-field} output_features[].preprocessing.normal_label
**Type** `string` · **Default** `normal` · the column's value that means normal; `anomaly` only ·
read by **data, train, quantize, export**

**Does** — names the value that means normal. Every other value is abnormal, and training learns
from the normal windows only.

**Change it** — when your column writes normal another way, such as `ok`.

**Extremes** — a value that does not occur, or training and validation parts without normal
windows, are refused ({rule}`DS-16`).
:::

:::{manifest-field} output_features[].preprocessing.normalization
**Type** `string` or `null` · **Default** `null` · `zscore`, `minmax`, `iq`, `null`; `number` only · read by
**data, train**

**Does** — scales the target before training, and unscales the model's answer afterwards.

**Default** — `null`, so the model answers in your column's own unit. That keeps
`mae_increase_max` meaningful: a budget in degrees stays in degrees.

**Change it** — when the target spans orders of magnitude and training struggles.

**Extremes** — with normalization on, your error budget is in scaled units, which is easy to
misread. Prefer leaving it off unless training demands otherwise.
:::

:::{manifest-field} output_features[].loss.type
**Type** `string` · **Default** `mean_squared_error` · `mean_squared_error`, `mean_absolute_error`, `huber`;
`number` only · read by **train**

**Does** — chooses what counts as a bad answer during training.

**Default** — `mean_squared_error`, the conventional starting point, which punishes large errors
hardest.

**Change it** — `mean_absolute_error` when your data has outliers you do not want dominating
training; `huber` for a compromise that behaves like the squared error near zero and the absolute
error far from it.

**Extremes** — squared error with a few extreme outliers trains a model that chases them at the
expense of every ordinary reading.
:::

:::{manifest-field} output_features[].loss.class_weights
**Type** `list` or `mapping` · **Default** none · one weight per class, or class → weight; `category` only ·
read by **train**

**Does** — makes some classes count for more during training.

**Default** — none: every class counts the same.

**Change it** — when the class you care about is rare. A fault that is 2% of your data is a class
the model can ignore and still score 98%.

**Extremes** — weights far from each other trade overall accuracy for recall on the rare class.
That may be exactly right, but it is a trade and the accuracy figure will show it.
:::

:::{manifest-field} output_features[].loss.positive_class_weight
**Type** `number` · **Default** none · greater than 0; `binary` only · read by **train**

**Does** — the same idea for a binary output: how much a positive counts against a negative.

**Default** — none, so both count the same.

**Change it** — when positives are rare and missing one is worse than a false alarm.

**Extremes** — a large weight produces a model that cries wolf. Tune it together with `threshold`,
and judge both on the confusion matrix rather than on accuracy.
:::

:::{manifest-field} output_features[].threshold
**Type** `number` · **Default** `0.5` · strictly between 0 and 1; `binary` only · read by **quantize, export**

**Does** — the score above which the answer is true. It is written into the export, so the board
and your computer decide identically.

**Default** — `0.5`, the neutral point.

**Change it** — to trade false alarms against misses without retraining. This is the cheapest knob
you have: lower it to catch more, raise it to cry wolf less.

**Extremes** — near 0 everything is true, near 1 nothing is. Both pass the quantization gate
happily, because the gate measures what 8-bit cost and not whether your threshold is sensible.
:::

:::{manifest-field} output_features[].clip
**Type** `list of two numbers` · **Default** none · `[low, high]`; `number` only · read by **build, export**

**Does** — bounds the model's answer to a range, inside the model.

**Default** — none: the model may answer anything.

**Change it** — when values outside a range are physically impossible and you would rather the model
never emit them than filter them in firmware.

**Extremes** — clipping inside the real range of your data silently caps correct answers, and the
error it causes looks like a model problem rather than a configuration one.
:::

:::{manifest-field} output_features[].accuracy_drop_max
**Type** `number` · **Default** none — required for `category` and `binary` · 0 to 1 · read by **quantize**

**Does** — the quantization gate's budget: how much test accuracy making the model 8-bit may cost.
`0.02` is two percentage points. Exceed it and the run fails, exports nothing, and writes a
per-layer table of where the accuracy went.

**Default** — none, and that is deliberate. This is a product decision, and no default could be
right for both a screening step and something that acts on its own.

**Change it** — from what happens when the model is wrong, not from what will pass.
[Budgets and gates](../../topics/budgets-and-gates.md) walks through choosing it.

**Extremes** — `0.0` is legitimate and often passes, because a small model on well-separated data
quantizes for free. A large value makes the gate decorative: there is no flag to skip it, so a
budget of `0.5` is how you accidentally disable it ({rule}`CF-16`,
{rule}`Q-4`).
:::

:::{manifest-field} output_features[].mae_increase_max
**Type** `number` · **Default** none — required for `number` · at least 0, in the column's unit · read by **quantize**

**Does** — the same gate for a numeric output, in mean absolute error. **MAE** is *mean absolute
error*: the average distance between the answer and the truth, so if the column is degrees, the
budget is in degrees.

**Default** — none, for the same reason.

**Change it** — from what the number is used for. An error that is invisible in a dashboard may be
unacceptable in a cut-off.

**Extremes** — with `preprocessing.normalization` set on the output, the unit is the scaled one
rather than your column's, which is the easiest way to set this field to something you did not mean.
:::

:::{manifest-field} output_features[].auc_drop_max
**Type** `number` · **Default** none — required for `anomaly` · 0 to 1 · read by **quantize**

**Does** — how much of the area under the ROC curve quantization may cost: how well the anomaly
score separates normal from abnormal test windows. It is the int8 budget of an `anomaly` output.

**Change it** — as for {mf}`output_features[].accuracy_drop_max`: from what a missed anomaly or a
false alarm costs.

**Extremes** — exceeding it fails the run ({rule}`CF-16`, {rule}`Q-4`); the test part needs both
normal and abnormal windows to measure it ({rule}`Q-5`).
:::

:::{manifest-field} output_features[].threshold_percentile
**Type** `number` · **Default** `95` · between 0 and 100, exclusive; `anomaly` only · read by
**quantize**

**Does** — sets the anomaly threshold: this percentile of the int8 model's scores on the validation
part's normal windows.

**Change it** — raise it for fewer false alarms, lower it to catch more anomalies.
`quantization.json` reports the detection and false alarm rates on the test part for the
threshold it chose.
:::
