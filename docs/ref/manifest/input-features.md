# The `input_features` section

One entry per column the model reads. A column no feature names is ignored, and every run lists it
under `ignored_columns`. What each type does inside the model is in
[feature types](../../topics/feature-types.md).

| Field | Type | Default |
|---|---|---|
| {mf}`input_features[].name` | string | — required |
| {mf}`input_features[].type` | string | — required |
| {mf}`input_features[].preprocessing.normalization` | string or null | `zscore` (number) |
| {mf}`input_features[].preprocessing.missing_value_strategy` | string | `fill_with_const` |
| {mf}`input_features[].preprocessing.fill_value` | number, string or boolean | per type |
| {mf}`input_features[].preprocessing.most_common` | integer | `32` (category) |
| {mf}`input_features[].preprocessing.vocab` | list | `derived` (category) |
| {mf}`input_features[].preprocessing.fallback_true_label` | string | none (binary) |
| {mf}`input_features[].encoder.type` | string | `dense` (category) |
| {mf}`input_features[].encoder.embedding_size` | integer | `derived` |

:::{manifest-field} input_features[].name
**Type** `string` · **Default** none — required · a column of the data, matching `[a-z][a-z0-9_]{0,31}`, each column at most
once · read by **every stage**

**Does** — names the column this feature reads. Naming a column is how you opt it in; there is no
exclude list to maintain.

**Default** — none. This is the one thing only you know.

**Change it** — when your column is called something else. The pattern is restrictive because the
name becomes a C identifier in the exported header.

**Extremes** — a name that is not a column of the data is refused ({rule}`DS-12`); so is
the same column twice ({rule}`CF-13`), and a name that collides with the output
({rule}`CF-11`).
:::

:::{manifest-field} input_features[].type
**Type** `string` · **Default** none — required · `number`, `category` or `binary` · read by **every stage**

**Does** — decides what the model is told about this column, what preprocessing is learned for it,
and what your firmware passes at run time.

**Default** — none. Guessing from the data would guess wrong on the case that matters: a column of
integers that is really a set of codes.

**Change it** — when you got it wrong, and the test for that is one question: *is 2 between 1 and
3?* Yes means `number`; no means `category`, even when the values are written as numbers; exactly
two values means `binary`.

**Extremes** — declaring an identifier as `number` is the mistake with the worst failure mode: the
model interpolates between device identities, works on your test split, and makes no sense when a
new device appears ({rule}`CF-14`).
:::

:::{manifest-field} input_features[].preprocessing.normalization
**Type** `string` or `null` · **Default** `zscore` for `number` · `zscore`, `minmax`, `iq`, `null`; `number`
only · read by **data, build**

**Does** — learns a shift and a scale from the training part and builds them into the model, so
that the model sees values around zero rather than around 40.0. `zscore` uses the mean and standard
deviation, `minmax` the minimum and range, `iq` the median and interquartile range.

**Default** — `zscore` suits a bell-shaped column, as most sensor readings are.

**Change it** — `minmax` when the column has hard physical limits; `iq` when outliers would
otherwise set the scale; `null` when the column is already in a sane range and you want nothing
done to it.

**Extremes** — `null` on a column measured in thousands alongside one measured in thousandths makes
the small one invisible to training. `minmax` on a column with one extreme outlier squeezes every
real value into a sliver of the range.
:::

:::{manifest-field} input_features[].preprocessing.missing_value_strategy
**Type** `string` · **Default** `fill_with_const` · `fill_with_const`, or `fill_with_mean` for `number` · read
by **data**

**Does** — decides what an empty cell becomes.

**Default** — `fill_with_const`, which uses `fill_value`, because it is predictable and needs
nothing learned from the data.

**Change it** — `fill_with_mean` for a `number` that measures something physical: zero is a real
temperature, and filling with it teaches the model that a missing reading means freezing.

**Extremes** — with many missing readings, either strategy invents a lot of data. If a column is
mostly empty, drop it rather than fill it.
:::

:::{manifest-field} input_features[].preprocessing.fill_value
**Type** `number`, `string` or `boolean` · **Default** `0.0` for `number`, `<UNK>` for `category`, `false` for
`binary` · a value of the column's kind · read by **data**

**Does** — the value a missing reading becomes under `fill_with_const`.

**Default** — a neutral value per type. `<UNK>` for a category is the same entry unseen values get,
which is the right place for "we do not know".

**Change it** — when zero means something in your column. A fill value outside the real range — for
instance `-1` for a count that is never negative — at least lets the model learn that the reading
was absent.

**Extremes** — a fill value inside the normal range is indistinguishable from a real reading, so the
model cannot learn that anything was missing.
:::

:::{manifest-field} input_features[].preprocessing.most_common
**Type** `integer` · **Default** `32` · at least 1; `category` only · read by **data**

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
:::

:::{manifest-field} input_features[].preprocessing.vocab
**Type** `list` · **Default** `derived` for `category` · your values, in your order · read by **data**

**Does** — pins the vocabulary and the code each value gets, instead of learning it from the data.

**Default** — `derived`, because the data knows which values occur and in what proportion.

**Change it** — when the codes must stay stable across retrains, because your firmware has the old
table compiled into it. Pinning is how you keep a deployed board correct.

**Extremes** — a pinned vocabulary missing a value that appears in the data sends it to "unknown"
silently. A pinned vocabulary longer than the data needs costs flash for entries nothing uses.
:::

:::{manifest-field} input_features[].preprocessing.fallback_true_label
**Type** `string` · **Default** none · the spelling that means true; `binary` only · read by **data**

**Does** — says which of two values is true, when they are not spellings Caravan recognises on its
own.

**Default** — none, and then the value that sorts second becomes true.

**Change it** — whenever your two values are not `yes`/`no`, `true`/`false`, `1`/`0`, `on`/`off` or
the like. For `ok`/`fault`, the sort rule would make `ok` true, which is the opposite of what anyone
means by a fault detector, so say so.

**Extremes** — relying on the sort rule works until someone renames a value, at which point the
meaning of your model inverts without anything failing ({rule}`DS-15`).
:::

:::{manifest-field} input_features[].encoder.type
**Type** `string` · **Default** `dense` for `category` · `dense` or `onehot`; `category` only · read by **build**

**Does** — decides how the model represents a category's code. `dense` learns a short vector per
value, an embedding; `onehot` gives each value its own position.

**Default** — `dense`, which is smaller as soon as the vocabulary is more than a handful.

**Change it** — `onehot` for a genuinely tiny vocabulary, where an embedding is overhead and the
one-hot form is simpler for the runtime.

**Extremes** — `onehot` over a 32-value vocabulary makes the first layer 32 times wider than it
needs to be, which lands in both flash and working memory.
:::

:::{manifest-field} input_features[].encoder.embedding_size
**Type** `integer` · **Default** `derived`: the smaller of the vocabulary size and 4 · at least 1; `dense` only ·
read by **build**

**Does** — how many numbers represent each value of the category.

**Default** — `derived`, capped at 4, because a microcontroller model has nothing to spare and four
dimensions separate a few dozen values perfectly well.

**Change it** — raise it when the category is the main signal and the model underfits; lower it to
reclaim flash.

**Extremes** — 1 collapses the category to a single ordered axis, which quietly reintroduces the
"is 2 between 1 and 3" problem that choosing `category` was meant to avoid. Very large wastes flash
on dimensions the data cannot fill.
:::
