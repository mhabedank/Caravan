# The `model` section

| Field | Type | Default |
|---|---|---|
| {mf}`model.name` | string | — required |
| {mf}`model.version` | string | — required |
| {mf}`model.template` | string | — required |
| {mf}`model.params` | mapping | `{}` |

:::{manifest-field} model.name
**Type** `string` · **Default** none — required · your model's name · read by **export**

**Does** — names the model in every report and in the exported C header, so that firmware printing
`model: <name> <version>` says which model it is actually running.

**Default** — none. A model without a name is a model nobody can refer to in a bug report.

**Change it** — when the model becomes a different model rather than a new version of this one.

**Extremes** — a name you later change breaks nothing in Caravan, but it does change what your
firmware prints, which is the thing a board run record is keyed on.
:::

:::{manifest-field} model.version
**Type** `string` · **Default** none — required · your model's version · read by **export**

**Does** — distinguishes this model from its earlier selves, in reports and in the export.

**Default** — none, for the same reason as the name.

**Change it** — every time you retrain for real. A board carrying weights from one version and a
label table from another is the failure this field exists to make visible.

**Extremes** — Caravan does not parse it or enforce an ordering; it is a label for you. Something
sortable is kinder to your future self than `final2`.
:::

:::{manifest-field} model.template
**Type** `string` · **Default** none — required · `mlp`, `conv1d`, `conv2d` or `autoencoder`
(`caravan templates` lists what is registered) · read by **build**

**Does** — chooses the shape of the model. You do not write layers; the template builds them from
`model.params`.

**Default** — none. There is no template that suits every kind of data, and picking one for you
would be picking wrong half the time.

**Change it** — when the other template suits your data better. [Templates](../../topics/templates.md)
has a table that picks one from data you can describe, and the short version is: `mlp` when the
*level* of your readings carries the signal, `conv1d` when the *shape over time* does, `conv2d`
for a plane or an image, and `autoencoder` for anomaly detection from normal data.

**Extremes** — an unregistered name is refused ({rule}`T-1`), and parameters that do not
belong to the named template are refused with it ({rule}`T-2`,
{rule}`CF-6`). A template must answer the output's type ({rule}`CF-18`), and only `conv2d` takes
an image ({rule}`CF-19`).
:::

:::{manifest-field} model.params
**Type** `mapping` · **Default** `{}` · the named template's parameters · read by **build**

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

**`conv2d`** is a convolution over a plane: a window seen as rows by input columns, or an image. It
answers `category`, `binary` and `number`, and it is the only template that takes an image. It
takes `blocks`, a list with at least one entry, each with `kind` (`standard`, the default, or
`separable` — a depthwise convolution with the block's kernel and stride, then a 1 × 1 convolution
with its filters), `filters`, `kernel` (an integer for a square, or `[rows, columns]`), and
optionally `stride` (1, an integer or `[rows, columns]`), `padding` (`valid` or `same`),
`normalise` (`false`, after each convolution of the block), `pool` (none; max pooling after the
block, an integer or `[rows, columns]`) and `dropout` (0); and `head`, `average` (default, average
pooling over the whole remaining plane) or `flatten`. A plane too small for the blocks on either
axis is refused ({rule}`CF-6`): at validation when the manifest gives the size, otherwise by the
build stage, before training.

**`autoencoder`** detects anomalies from normal data. It answers the `anomaly` output and nothing
else ({rule}`CF-18`). It takes `encoder`, a list of dense widths from the input towards the code,
at least one; `code`, the width of the linear bottleneck; `decoder`, a list of widths back out,
default the encoder reversed; and `dropout`, from 0 up to but not including 1, default 0.
:::
