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
**Type** `string` · **Default** none — required · `mlp` or `conv1d` (`caravan templates` lists what is registered) · read by
**build**

**Does** — chooses the shape of the model. You do not write layers; the template builds them from
`model.params`.

**Default** — none. There is no template that suits every kind of data, and picking one for you
would be picking wrong half the time.

**Change it** — when the other template suits your data better. [Templates](../../topics/templates.md)
has a table that picks one from data you can describe, and the short version is: `mlp` when the
*level* of your readings carries the signal, `conv1d` when the *shape over time* does.

**Extremes** — an unregistered name is refused ({rule}`T-1`), and parameters that do not
belong to the named template are refused with it ({rule}`T-2`,
{rule}`CF-6`).
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
:::
