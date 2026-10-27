# Manifest reference

One YAML file per model version, schema `caravan/v0.2`.

This page is a lookup. Each section opens with a table of its fields for scanning, and then gives
every setting an entry that answers four questions:

- **Does** — what it changes about the model or the run.
- **Default** — why the default is what it is.
- **Change it** — the situation that calls for another value.
- **Extremes** — what goes wrong at either end.

If you are choosing rather than looking up, the concept pages are the better start:
[feature types](../concepts/feature-types.md) for `number`, `category` and `binary`;
[templates](../concepts/templates.md) for `mlp` and `conv1d`;
[budgets and gates](../concepts/budgets-and-gates.md) for the two checks that can stop a run.

**Two terms used throughout.** The **training part** is the share of windows the model learns from;
validation and test are the other two. **`derived`** means the value is learned from the training
part by the `data` stage and written into each run's `resolved-manifest.yaml`.

**`caravan render <manifest> --stdout`** prints any manifest with every default filled in, which is
faster than reading this page when you only want to know what you are actually running.

The names follow [Ludwig](https://ludwig.ai)'s wherever Ludwig has the concept, because Caravan
borrowed the idea of declaring a type per column rather than inventing a vocabulary for it. Only
types and options that can run inside a model on a microcontroller exist here.

## Top level

| Field | Type | Default |
|---|---|---|
| `apiVersion` | string | — required |
| `dataset` | string | — required |
| `random_seed` | integer | `42` |

### `apiVersion`

`string` · required · must be `caravan/v0.2` · read by **every stage**

**Does** — declares which schema the file is written in, so Caravan can refuse a file it would
otherwise misread.

**Default** — none, deliberately. A file without a version was once read as the oldest known
schema, and that guessed wrong silently; it is now an error ([V-1](rules.md#v-1)).

**Change it** — only when migrating to a new schema. A manifest of the previous schema,
`caravan/v0.1`, is refused with a pointer to [the change notes](../manifest-changes.md), and each
key that moved is refused at its old path naming its new one.

**Extremes** — not applicable: one value is accepted.

### `dataset`

`string` · required · a directory of `.csv`, `.tsv` or `.txt` files with a header row, or one such
file, relative to the manifest · read by **data**

**Does** — points at your data. Files in a directory are read in path order as one sequence of
records, oldest first, each with the same header row. An empty cell is a missing reading.

**Default** — none. There is nothing sensible to guess, and guessing would read the wrong data.

**Change it** — whenever the data moves. This is the one line that turns the worked example into
your own project.

**Extremes** — a directory whose files disagree on their header is refused; so is a file with no
header row. Your data is never copied into a run directory: Caravan reads it and records its
digest, so keeping it out of anything you publish stays your decision
([DS-1](rules.md#ds-1) to [DS-15](rules.md#ds-15)).

### `random_seed`

`integer` · default `42` · any · read by **data, build, train, quantize, export**

**Does** — fixes every random choice: the split, the weight initialisation, the shuffling, the
calibration sample. The same manifest and the same data give the same model.

**Default** — `42` is arbitrary and conventional. What matters is that there is one, so that a run
is reproducible without anybody having to think about it.

**Change it** — to find out how much of a result is the seed. Train the same manifest under three
seeds and you learn whether an accuracy figure is a property of your data or of one lucky draw.

**Extremes** — none in value, but note what it does *not* fix: a different framework version, or
different hardware, can still move the last decimal. The provenance of a number is in the run
report, not in the seed alone.

## `model`

| Field | Type | Default |
|---|---|---|
| `model.name` | string | — required |
| `model.version` | string | — required |
| `model.template` | string | — required |
| `model.params` | mapping | `{}` |

### `model.name`

`string` · required · your model's name · read by **export**

**Does** — names the model in every report and in the exported C header, so that firmware printing
`model: <name> <version>` says which model it is actually running.

**Default** — none. A model without a name is a model nobody can refer to in a bug report.

**Change it** — when the model becomes a different model rather than a new version of this one.

**Extremes** — a name you later change breaks nothing in Caravan, but it does change what your
firmware prints, which is the thing a board run record is keyed on.

### `model.version`

`string` · required · your model's version · read by **export**

**Does** — distinguishes this model from its earlier selves, in reports and in the export.

**Default** — none, for the same reason as the name.

**Change it** — every time you retrain for real. A board carrying weights from one version and a
label table from another is the failure this field exists to make visible.

**Extremes** — Caravan does not parse it or enforce an ordering; it is a label for you. Something
sortable is kinder to your future self than `final2`.

### `model.template`

`string` · required · `mlp` or `conv1d` (`caravan templates` lists what is registered) · read by
**build**

**Does** — chooses the shape of the model. You do not write layers; the template builds them from
`model.params`.

**Default** — none. There is no template that suits every kind of data, and picking one for you
would be picking wrong half the time.

**Change it** — when the other template suits your data better. [Templates](../concepts/templates.md)
has a table that picks one from data you can describe, and the short version is: `mlp` when the
*level* of your readings carries the signal, `conv1d` when the *shape over time* does.

**Extremes** — an unregistered name is refused ([T-1](rules.md#t-1)), and parameters that do not
belong to the named template are refused with it ([T-2](rules.md#t-2),
[CF-6](rules.md#cf-6)).

### `model.params`

`mapping` · default `{}` · the named template's parameters · read by **build**

**Does** — the template's own settings. Each template accepts its own set and refuses the rest.

**Default** — `{}`, which means every parameter takes the template's own default. A manifest that
names only a template trains something.

**Change it** — when the model underfits (train accuracy already poor: go wider or deeper) or
overfits (train far better than test: add `dropout`).

**Extremes** — a wide `mlp` over a long window grows very fast, because the window is flattened:
`hidden: [4096, 4096]` on a small window already exceeds the flash of a 4 MB board, and the fit
check stops it before training. That is the intended behaviour, not a limitation.

**`mlp`** takes `hidden`, a list of layer widths with at least one entry, and `dropout`, from 0 up
to but not including 1, default 0.

**`conv1d`** takes `blocks`, a list with at least one entry, each with `filters`, `kernel`, and
optionally `stride` (1), `padding` (`valid` or `same`), `normalise` (`false`), `pool` (none) and
`dropout` (0); and `head`, either `average` (default) or `flatten`.

## `input_features[]`

One entry per column the model reads. A column no feature names is ignored, and every run lists it
under `ignored_columns`. What each type does inside the model is in
[feature types](../concepts/feature-types.md).

| Field | Type | Default |
|---|---|---|
| `input_features[].name` | string | — required |
| `input_features[].type` | string | — required |
| `input_features[].preprocessing.normalization` | string or null | `zscore` (number) |
| `input_features[].preprocessing.missing_value_strategy` | string | `fill_with_const` |
| `input_features[].preprocessing.fill_value` | number, string or boolean | per type |
| `input_features[].preprocessing.most_common` | integer | `32` (category) |
| `input_features[].preprocessing.vocab` | list | `derived` (category) |
| `input_features[].preprocessing.fallback_true_label` | string | none (binary) |
| `input_features[].encoder.type` | string | `dense` (category) |
| `input_features[].encoder.embedding_size` | integer | `derived` |

### `input_features[].name`

`string` · required · a column of the data, matching `[a-z][a-z0-9_]{0,31}`, each column at most
once · read by **every stage**

**Does** — names the column this feature reads. Naming a column is how you opt it in; there is no
exclude list to maintain.

**Default** — none. This is the one thing only you know.

**Change it** — when your column is called something else. The pattern is restrictive because the
name becomes a C identifier in the exported header.

**Extremes** — a name that is not a column of the data is refused ([DS-12](rules.md#ds-12)); so is
the same column twice ([CF-13](rules.md#cf-13)), and a name that collides with the output
([CF-11](rules.md#cf-11)).

### `input_features[].type`

`string` · required · `number`, `category` or `binary` · read by **every stage**

**Does** — decides what the model is told about this column, what preprocessing is learned for it,
and what your firmware passes at run time.

**Default** — none. Guessing from the data would guess wrong on the case that matters: a column of
integers that is really a set of codes.

**Change it** — when you got it wrong, and the test for that is one question: *is 2 between 1 and
3?* Yes means `number`; no means `category`, even when the values are written as numbers; exactly
two values means `binary`.

**Extremes** — declaring an identifier as `number` is the mistake with the worst failure mode: the
model interpolates between device identities, works on your test split, and makes no sense when a
new device appears ([CF-14](rules.md#cf-14)).

### `input_features[].preprocessing.normalization`

`string` or `null` · default `zscore` for `number` · `zscore`, `minmax`, `iq`, `null`; `number`
only · read by **data, build**

**Does** — learns a shift and a scale from the training part and builds them into the model, so
that the model sees values around zero rather than around 40.0. `zscore` uses the mean and standard
deviation, `minmax` the minimum and range, `iq` the median and interquartile range.

**Default** — `zscore` suits a roughly bell-shaped column, which most sensor readings are.

**Change it** — `minmax` when the column has hard physical limits; `iq` when outliers would
otherwise set the scale; `null` when the column is already in a sane range and you want nothing
done to it.

**Extremes** — `null` on a column measured in thousands alongside one measured in thousandths makes
the small one invisible to training. `minmax` on a column with one extreme outlier squeezes every
real value into a sliver of the range.

### `input_features[].preprocessing.missing_value_strategy`

`string` · default `fill_with_const` · `fill_with_const`, or `fill_with_mean` for `number` · read
by **data**

**Does** — decides what an empty cell becomes.

**Default** — `fill_with_const`, which uses `fill_value`, because it is predictable and needs
nothing learned from the data.

**Change it** — `fill_with_mean` for a `number`, which is usually the better answer: zero is a real
temperature, and filling with it teaches the model that a missing reading means freezing.

**Extremes** — with many missing readings, either strategy invents a lot of data. If a column is
mostly empty, the honest move is to drop it rather than to fill it.

### `input_features[].preprocessing.fill_value`

`number`, `string` or `boolean` · default `0.0` for `number`, `<UNK>` for `category`, `false` for
`binary` · a value of the column's kind · read by **data**

**Does** — the value a missing reading becomes under `fill_with_const`.

**Default** — a neutral value per type. `<UNK>` for a category is the same entry unseen values get,
which is the right place for "we do not know".

**Change it** — when zero means something in your column. A fill value outside the real range — for
instance `-1` for a count that is never negative — at least lets the model learn that the reading
was absent.

**Extremes** — a fill value inside the normal range is indistinguishable from a real reading, so the
model cannot learn that anything was missing.

### `input_features[].preprocessing.most_common`

`integer` · default `32` · at least 1; `category` only · read by **data**

**Does** — how many distinct values get their own entry in the vocabulary. The most frequent values
in the training part are kept, ordered by frequency then alphabetically; everything else becomes
one "unknown" entry.

**Default** — `32` keeps a small embedding and a small model, which is the point on a
microcontroller.

**Change it** — raise it when your column has more meaningful values than that and the rare ones
matter; lower it when the tail is noise and you want the model to stop paying for it.

**Extremes** — too low and most of your data collapses into "unknown", which is a model that cannot
tell your devices apart. Too high and the embedding grows with the vocabulary, in flash you may not
have.

### `input_features[].preprocessing.vocab`

`list` · default `derived` for `category` · your values, in your order · read by **data**

**Does** — pins the vocabulary and the code each value gets, instead of learning it from the data.

**Default** — `derived`, because the data knows which values occur and in what proportion.

**Change it** — when the codes must stay stable across retrains, because your firmware has the old
table compiled into it. Pinning is how you keep a deployed board correct.

**Extremes** — a pinned vocabulary missing a value that appears in the data sends it to "unknown"
silently. A pinned vocabulary longer than the data needs costs flash for entries nothing uses.

### `input_features[].preprocessing.fallback_true_label`

`string` · default none · the spelling that means true; `binary` only · read by **data**

**Does** — says which of two values is true, when they are not spellings Caravan recognises on its
own.

**Default** — none, and then the value that sorts second becomes true.

**Change it** — whenever your two values are not `yes`/`no`, `true`/`false`, `1`/`0`, `on`/`off` or
the like. For `ok`/`fault`, the sort rule would make `ok` true, which is the opposite of what anyone
means by a fault detector, so say so.

**Extremes** — relying on the sort rule works until someone renames a value, at which point the
meaning of your model inverts without anything failing ([DS-15](rules.md#ds-15)).

### `input_features[].encoder.type`

`string` · default `dense` for `category` · `dense` or `onehot`; `category` only · read by **build**

**Does** — decides how the model represents a category's code. `dense` learns a short vector per
value, an embedding; `onehot` gives each value its own position.

**Default** — `dense`, which is smaller as soon as the vocabulary is more than a handful.

**Change it** — `onehot` for a genuinely tiny vocabulary, where an embedding is overhead and the
one-hot form is simpler for the runtime.

**Extremes** — `onehot` over a 32-value vocabulary makes the first layer 32 times wider than it
needs to be, which lands in both flash and working memory.

### `input_features[].encoder.embedding_size`

`integer` · default `derived`: the smaller of the vocabulary size and 4 · at least 1; `dense` only ·
read by **build**

**Does** — how many numbers represent each value of the category.

**Default** — `derived`, capped at 4, because a microcontroller model has nothing to spare and four
dimensions separate a few dozen values perfectly well.

**Change it** — raise it when the category is the main signal and the model underfits; lower it to
reclaim flash.

**Extremes** — 1 collapses the category to a single ordered axis, which quietly reintroduces the
"is 2 between 1 and 3" problem that choosing `category` was meant to avoid. Very large wastes flash
on dimensions the data cannot fill.

## `output_features[]`

Exactly one entry: the column the model answers ([CF-17](rules.md#cf-17)).

| Field | Type | Default |
|---|---|---|
| `output_features[].name` | string | — required |
| `output_features[].type` | string | — required |
| `output_features[].preprocessing.vocab` | list | `derived` |
| `output_features[].preprocessing.fallback_true_label` | string | none |
| `output_features[].preprocessing.normalization` | string or null | `null` |
| `output_features[].loss.type` | string | `mean_squared_error` (number) |
| `output_features[].loss.class_weights` | list or mapping | none |
| `output_features[].loss.positive_class_weight` | number | none |
| `output_features[].threshold` | number | `0.5` (binary) |
| `output_features[].clip` | list of two numbers | none |
| `output_features[].accuracy_drop_max` | number | — required for category and binary |
| `output_features[].mae_increase_max` | number | — required for number |

### `output_features[].name`

`string` · required · a column of the data · read by **every stage**

**Does** — names the column the model answers.

**Default** — none.

**Change it** — when you are predicting something else.

**Extremes** — a name that is also an input feature is refused ([CF-11](rules.md#cf-11)); so is one
that is not a column of the data ([CF-9](rules.md#cf-9)).

### `output_features[].type`

`string` · required · `category`, `binary` or `number` · read by **every stage**

**Does** — decides what the model learns to produce, which budget field applies, and how an answer
is turned into a decision: a category takes the argmax, a binary compares with `threshold`, a number
is the value itself.

**Default** — none.

**Change it** — when the question changes. Two classes can be modelled either way; `binary` is the
smaller model and gives you a threshold to tune, `category` generalises to more classes later.

**Extremes** — `number` on something that is really a set of labels produces answers between the
labels, which mean nothing ([CF-14](rules.md#cf-14)).

### `output_features[].preprocessing.vocab`

`list` · default `derived`: by frequency in the training part · every class of the data, in your
order · `category` only · read by **data**

**Does** — pins the class order, which is the order of the scores the model outputs and the order
of the labels in the exported header.

**Default** — `derived`, by frequency in the training part.

**Change it** — when your firmware has the old label order compiled into it. Pinning here is how a
retrained model stays compatible with a deployed board.

**Extremes** — a class present in the data but missing from a pinned vocabulary is an error, not a
silent drop ([DS-5](rules.md#ds-5), [DS-11](rules.md#ds-11), [DS-14](rules.md#ds-14)).

### `output_features[].preprocessing.fallback_true_label`

`string` · default none · `binary` only · read by **data**

**Does** — as for an input feature: which of two spellings means true.

**Default** — none, and the value that sorts second becomes true.

**Change it** — for any pair Caravan does not recognise. On the output this matters more than on an
input, because it decides what your model's "yes" means ([DS-15](rules.md#ds-15)).

**Extremes** — getting it wrong inverts every answer while every metric still looks plausible.

### `output_features[].preprocessing.normalization`

`string` or `null` · default `null` · `zscore`, `minmax`, `iq`, `null`; `number` only · read by
**data, train**

**Does** — scales the target before training, and unscales the model's answer afterwards.

**Default** — `null`, so the model answers in your column's own unit. That keeps
`mae_increase_max` meaningful: a budget in degrees stays in degrees.

**Change it** — when the target spans orders of magnitude and training struggles.

**Extremes** — with normalization on, your error budget is in scaled units, which is easy to
misread. Prefer leaving it off unless training demands otherwise.

### `output_features[].loss.type`

`string` · default `mean_squared_error` · `mean_squared_error`, `mean_absolute_error`, `huber`;
`number` only · read by **train**

**Does** — chooses what counts as a bad answer during training.

**Default** — `mean_squared_error`, the conventional starting point, which punishes large errors
hardest.

**Change it** — `mean_absolute_error` when your data has outliers you do not want dominating
training; `huber` for a compromise that behaves like the squared error near zero and the absolute
error far from it.

**Extremes** — squared error with a few extreme outliers trains a model that chases them at the
expense of every ordinary reading.

### `output_features[].loss.class_weights`

`list` or `mapping` · default none · one weight per class, or class → weight; `category` only ·
read by **train**

**Does** — makes some classes count for more during training.

**Default** — none: every class counts the same.

**Change it** — when the class you care about is rare. A fault that is 2% of your data is a class
the model can ignore and still score 98%.

**Extremes** — weights far from each other trade overall accuracy for recall on the rare class.
That may be exactly right, but it is a trade and the accuracy figure will show it.

### `output_features[].loss.positive_class_weight`

`number` · default none · greater than 0; `binary` only · read by **train**

**Does** — the same idea for a binary output: how much a positive counts against a negative.

**Default** — none, so both count the same.

**Change it** — when positives are rare and missing one is worse than a false alarm.

**Extremes** — a large weight produces a model that cries wolf. Tune it together with `threshold`,
and judge both on the confusion matrix rather than on accuracy.

### `output_features[].threshold`

`number` · default `0.5` · strictly between 0 and 1; `binary` only · read by **quantize, export**

**Does** — the score above which the answer is true. It is written into the export, so the board
and your computer decide identically.

**Default** — `0.5`, the neutral point.

**Change it** — to trade false alarms against misses without retraining. This is the cheapest knob
you have: lower it to catch more, raise it to cry wolf less.

**Extremes** — near 0 everything is true, near 1 nothing is. Both pass the quantization gate
happily, because the gate measures what 8-bit cost and not whether your threshold is sensible.

### `output_features[].clip`

`list of two numbers` · default none · `[low, high]`; `number` only · read by **build, export**

**Does** — bounds the model's answer to a range, inside the model.

**Default** — none: the model may answer anything.

**Change it** — when values outside a range are physically impossible and you would rather the model
never emit them than filter them in firmware.

**Extremes** — clipping inside the real range of your data silently caps correct answers, and the
error it causes looks like a model problem rather than a configuration one.

### `output_features[].accuracy_drop_max`

`number` · required for `category` and `binary` · 0 to 1 · read by **quantize**

**Does** — the quantization gate's budget: how much test accuracy making the model 8-bit may cost.
`0.02` is two percentage points. Exceed it and the run fails, exports nothing, and writes a
per-layer table of where the accuracy went.

**Default** — none, and that is deliberate. This is a product decision, and no default could be
right for both a screening step and something that acts on its own.

**Change it** — from what happens when the model is wrong, not from what will pass.
[Budgets and gates](../concepts/budgets-and-gates.md) walks through choosing it.

**Extremes** — `0.0` is legitimate and often passes, because a small model on well-separated data
quantizes for free. A large value makes the gate decorative: there is no flag to skip it, so a
budget of `0.5` is how you accidentally disable it ([CF-16](rules.md#cf-16),
[Q-4](rules.md#q-4)).

### `output_features[].mae_increase_max`

`number` · required for `number` · at least 0, in the column's unit · read by **quantize**

**Does** — the same gate for a numeric output, in mean absolute error. **MAE** is *mean absolute
error*: the average distance between the answer and the truth, so if the column is degrees, the
budget is in degrees.

**Default** — none, for the same reason.

**Change it** — from what the number is used for. An error that is invisible in a dashboard may be
unacceptable in a cut-off.

**Extremes** — with `preprocessing.normalization` set on the output, the unit is the scaled one
rather than your column's, which is the easiest way to set this field to something you did not mean.

## `preprocessing`

| Field | Type | Default |
|---|---|---|
| `preprocessing.window_size` | integer | — required by both templates |
| `preprocessing.split.type` | string | `random` |
| `preprocessing.split.probabilities` | list of three numbers | `[0.7, 0.15, 0.15]` |
| `preprocessing.split.column` | string | the output's column, for `stratify` |

### `preprocessing.window_size`

`integer` · required by templates that consume a window, which both do · at least 1 · read by
**every stage**

**Does** — how many consecutive records form one sample. Windows never overlap, and a window whose
records disagree about the output is discarded and counted.

**Default** — none. It comes from your physics, not from the model: how many time steps it takes to
see the thing you want to recognise.

**Change it** — when the phenomenon is longer or shorter than you thought. Because windows do not
overlap, this also sets how many samples you have: halving the window roughly doubles them.

**Extremes** — too long and you have few samples and mixed windows get discarded; too short and the
pattern does not fit inside one. A window longer than your shortest labelled stretch produces no
usable samples for that class at all ([CF-6](rules.md#cf-6),
[DS-6](rules.md#ds-6)).

### `preprocessing.split.type`

`string` · default `random` · `random`, `stratify` or `fixed` · read by **data, train, quantize,
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
([CF-12](rules.md#cf-12), [CF-15](rules.md#cf-15)).

### `preprocessing.split.probabilities`

`list of three numbers` · default `[0.7, 0.15, 0.15]` · train, validation, test; each above 0,
summing to 1; not allowed with `fixed` · read by **data, train, quantize, export**

**Does** — the shares of the three parts.

**Default** — `[0.7, 0.15, 0.15]`, the usual compromise between having enough to learn from and
enough to measure on.

**Change it** — give the test part more when a metric needs to mean something on a small dataset,
and less when there is barely enough to train.

**Extremes** — a tiny test part makes accuracy jump in large steps: with 12 test windows, one
changed prediction moves accuracy by 8 points, which is larger than a typical quantization budget.
The run report states the resolution for exactly this reason
([CF-1](rules.md#cf-1), [DS-8](rules.md#ds-8)).

### `preprocessing.split.column`

`string` · default the output's column for `stratify` · for `stratify`, the output's column; for
`fixed`, the column naming each record's part · read by **data, train, quantize, export**

**Does** — with `stratify`, the column whose classes are balanced across parts. With `fixed`, the
column in which every record names its part, as `train`, `validation` or `test`, or as Ludwig's
`0`, `1`, `2`.

**Default** — the output's column, which is what stratifying almost always means.

**Change it** — with `fixed`, to whichever column you added for the purpose.

**Extremes** — a window whose records name two different parts is discarded. The split column is
never a feature, so it cannot leak into the model
([CF-13](rules.md#cf-13), [DS-13](rules.md#ds-13)).

## `defaults`

Preprocessing and encoder settings applied to **every input feature of one type**, so that a
manifest with twenty numeric columns does not repeat itself twenty times. `<type>` is `number`,
`category` or `binary`.

Precedence, highest first: a feature's own value, then the type's entry here, then the type's
built-in default.

Each field mirrors the per-feature setting of the same name exactly — the entries above are the
documentation for both:

`defaults.<type>.preprocessing.normalization`,
`defaults.<type>.preprocessing.missing_value_strategy`,
`defaults.<type>.preprocessing.fill_value`,
`defaults.<type>.preprocessing.most_common`,
`defaults.<type>.preprocessing.vocab`,
`defaults.<type>.preprocessing.fallback_true_label`,
`defaults.<type>.encoder.type`,
`defaults.<type>.encoder.embedding_size`.

**One caution.** `defaults.<type>.preprocessing.vocab` and
`defaults.<type>.preprocessing.fallback_true_label` pin a value for *every* column of that type,
and two columns rarely share a vocabulary. These two are nearly always per-feature settings.

## `trainer`

| Field | Type | Default |
|---|---|---|
| `trainer.epochs` | integer | `50` |
| `trainer.batch_size` | integer | `256` |
| `trainer.learning_rate` | number | `0.001` |
| `trainer.optimizer.type` | string | `adam` |
| `trainer.early_stop` | integer | `5` |

### `trainer.epochs`

`integer` · default `50` · at least 1 · read by **train**

**Does** — the maximum number of passes over the training part. `early_stop` usually ends training
first, and the best checkpoint is kept rather than the last.

**Default** — `50`, enough for a small model on a small dataset to converge.

**Change it** — raise it when training is still improving when it stops; lower it to iterate faster
while you are still deciding on columns and types.

**Extremes** — too few and the model never converges; too many costs time but little else, because
the best checkpoint is what is kept.

### `trainer.batch_size`

`integer` · default `256` · at least 1 · read by **train**

**Does** — how many windows the model sees before each weight update.

**Default** — `256`, which trains quickly on a dataset of a few thousand windows.

**Change it** — lower it when you have few windows, so there are enough updates per epoch to learn
anything. A dataset of 80 windows and a batch of 256 gets one update per epoch.

**Extremes** — very small batches train slowly and noisily; very large ones on a small dataset
barely train at all.

### `trainer.learning_rate`

`number` · default `0.001` · greater than 0 · read by **train**

**Does** — how far the weights move at each update.

**Default** — `0.001`, the conventional starting point for the default optimizer.

**Change it** — lower it when the loss jumps around or diverges; raise it when training is
converging far too slowly to wait for.

**Extremes** — too high and the loss diverges or oscillates and never settles; too low and training
ends on `epochs` long before it has learned anything ([DS-10](rules.md#ds-10)).

### `trainer.optimizer.type`

`string` · default `adam` · `adam`, `sgd` or `adamw` · read by **train**

**Does** — chooses the algorithm that applies the updates.

**Default** — `adam`, which needs the least tuning and is why the default learning rate works
without being thought about.

**Change it** — `adamw` when the model overfits and you want weight decay as well as `dropout`;
`sgd` only when you are deliberately reproducing a recipe that asks for it.

**Extremes** — `sgd` with the `adam` default learning rate usually trains badly: the two want
different rates, so changing the optimizer means revisiting `learning_rate`.

### `trainer.early_stop`

`integer` · default `5` · epochs without an improvement in validation loss before stopping; `-1`
never stops · read by **train**

**Does** — stops training when the validation loss has not improved for this many epochs, and keeps
the best checkpoint rather than the last.

**Default** — `5`, patient enough to ride out a noisy epoch and short enough not to waste minutes.

**Change it** — raise it when your validation loss is noisy on a small validation part; set `-1`
when you want all `epochs` regardless.

**Extremes** — `1` stops on the first bad epoch, which on a small validation part is luck rather
than evidence. `-1` with large `epochs` is only slower, since the best checkpoint still wins.

## `export`

| Field | Type | Default |
|---|---|---|
| `export.targets` | list of strings | — required |
| `export.quantization` | string | `int8` |
| `export.formats` | list of strings | `[flatbuffer, c_array]` |
| `export.representative_samples` | integer | — required for `int8` |
| `export.test_windows` | integer | `0` |

### `export.targets`

`list of strings` · required · board identifiers from `caravan boards`, each at most once · read by
**build (the fit check), export**

**Does** — names the boards the model must fit. Before training, the fit check compares the model's
weights and a floor on its working memory against each board and fails if one cannot possibly hold
it. It also decides which runner skeletons the export writes.

**Default** — none. A model for a microcontroller without a named microcontroller has no budget,
and the budget is the reason this project exists.

**Change it** — when the hardware changes. Naming more than one board is normal and the check runs
against all of them.

**Extremes** — an unknown identifier is refused ([B-1](rules.md#b-1)). A model far too large fails
the fit check in seconds with the exact shortfall, before training ([F-1](rules.md#f-1)) — a
passing check is not a promise that it fits, because its figures are `estimated` lower bounds.

### `export.quantization`

`string` · default `int8` · `int8`, `float16` or `none` · read by **build (the fit check),
quantize, export**

**Does** — the numeric format the model is converted to.

**Default** — `int8`. It is what makes a model fit and run on a microcontroller, so it is the
format rather than an optimisation applied at the end.

**Change it** — rarely. `float16` or `none` exist for comparison and for hardware with a usable
floating-point unit, and both make the model larger.

**Extremes** — away from `int8` the accuracy gate has little to measure, and the model may stop
fitting the boards you named. `int8` requires `export.representative_samples`
([Q-3](rules.md#q-3)).

### `export.formats`

`list of strings` · default `[flatbuffer, c_array]` · `flatbuffer`, `c_array` · read by **export**

**Does** — which forms of the model are written. `flatbuffer` is `model.tflite`; `c_array` is the
`.h` and `.cc` pair your firmware compiles.

**Default** — both, because you almost always want both: the file to inspect and the array to
build.

**Change it** — drop `c_array` if nothing will compile the model, and keep in mind that
`export.test_windows` needs it.

**Extremes** — `onnx` is refused rather than silently ignored ([X-1](rules.md#x-1)).

### `export.representative_samples`

`integer` · required for `int8` · at least 100 · read by **quantize**

**Does** — how many training windows are run through the model to learn the range of every tensor,
which is what int8 conversion needs in order to choose its scales.

**Default** — none, and it is required for `int8`, because a calibration set chosen for you is a
silent accuracy decision.

**Change it** — raise it when the gate fails and you suspect calibration rather than the model.
When the training part holds fewer windows than you ask for, all of them are used and the report
says so.

**Extremes** — too few and the scales are set by an unrepresentative sample, which costs accuracy
in exactly the way the gate then catches. Very many only costs conversion time
([CF-4](rules.md#cf-4)).

### `export.test_windows`

`integer` · default `0` · 0 to 64; above 0 needs `c_array` in `export.formats` · read by **export**

**Does** — writes `model/test_windows.h`: that many windows of the test part as raw values, every
class in turn, together with what the data says and what the int8 model answered on your computer.
A [board run](../route/3-onto-a-board.md) compares the board's answers with these.

**Default** — `0`, which writes none. Your data enters an export only when you ask it to, and that
default is the safe one.

**Change it** — set it to 16 before leg 3. Without it, "the board works" can only mean "the board
did not crash".

**Extremes** — when the test part holds fewer windows than you ask for, all of them are written and
`export.json` says so. The upper bound of 64 keeps the generated header readable and the board run
short. Remember that these windows are **your data, in a header file**: it is a file to keep out of
anything you publish.

## A complete example

The example from [leg 1](../route/1-first-model.md), on the synthetic data that comes with Caravan:

```yaml
apiVersion: caravan/v0.2

model:
  name: picket-mlp
  version: 0.2.0
  template: mlp
  params:
    hidden: [32, 16]
    dropout: 0.1

input_features:
  - name: can_id
    type: category
  - {name: dlc, type: number}
  - {name: b0, type: number}
  - {name: b1, type: number}
  - {name: b2, type: number}

output_features:
  - name: label
    type: category
    accuracy_drop_max: 0.02

preprocessing:
  window_size: 64
  split: {type: stratify, column: label, probabilities: [0.7, 0.15, 0.15]}

dataset: ../tests/fixtures/datasets/synthetic

trainer: {epochs: 50, batch_size: 256, learning_rate: 0.001, early_stop: 5}
random_seed: 42

export:
  quantization: int8
  formats: [flatbuffer, c_array]
  targets: [s32k144, stm32h743, esp32]
  representative_samples: 500
  test_windows: 16
```
