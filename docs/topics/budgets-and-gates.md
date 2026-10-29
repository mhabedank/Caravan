# Budgets and gates

:::{admonition} You will learn
:class: learn
- the two checks that can stop a run, and when each one runs;
- what a pass of the fit check is worth, and what it is not;
- how to choose a budget from what a wrong answer costs;
- why 8-bit is the format, not an optimisation.
:::

Caravan has two {term}`gates <gate>`, two checks that can stop a run. Neither can be turned off, and that is deliberate: a
check you can silence with a flag becomes a check that is always silenced, and then the budget that
was the whole reason for building an embedded model stops being real.

They answer different questions at different moments.

## The fit check: can this model possibly fit?

**When:** after the model is built, *before* training starts.

**What it compares:** the size of the weights at the stated {mf}`export.quantization`, and a
computed floor on the working memory the model needs, against what each {term}`board` in
{mf}`export.targets` has.

**What happens:** if a floor exceeds what a board offers, the run fails before training, under rule
{rule}`F-1`. No amount of training can make that model fit, so the time would be spent to reach the
same answer an hour later.

**What a pass is worth:** not much on its own. The check
uses only figures that bound the need *from below*, and it labels its numbers
<span class="prov estimated">estimated</span>. A model it stops cannot fit. A model it passes
*might* fit — the runtime plans its own memory on the device with its own allocator, so the figure
that actually decides is established further up the ladder, on an emulator or on the board itself.

This is the one check in Caravan allowed to pass without determining whether the budget holds, and
it is allowed only because it is not the gate.

## The quantization gate: did making it 8-bit cost too much?

**When:** after training, after the model has been converted to {term}`int8`.

**What it compares:** the int8 model's quality against the trained model's, on the
{term}`test part`.

**What you set:** one number per output, in the manifest.

- {mf}`accuracy_drop_max <output_features[].accuracy_drop_max>` — for a `category` or `binary` output. How much test accuracy you will give
  up. `0.02` means two percentage points.
- {mf}`mae_increase_max <output_features[].mae_increase_max>` — for a `number` output. How much
  the mean absolute error may grow, in the column's own unit. **{term}`MAE`** is
  *mean absolute error*: the average distance between the answer and
  the truth, so if the column is degrees, the budget is in degrees.

**What happens when it is exceeded:** the run fails with exit code `1` under rule {rule}`Q-4`,
exports nothing, and
writes a **per-layer table of where the accuracy went**. That table is the point. A verdict tells
you that you have a problem; the table tells you which layer turned 8-bit badly, which is the only
thing you can act on.

There is no flag, environment variable or option that lowers or skips this. Loosening a budget means
editing the manifest, which shows up in a diff and in review. That is the intended cost.

## Choosing the number

The {term}`budget` is not a modelling parameter; it is a product decision written in a modelling
file. Ask what the model is for.

- **A screening step that a human or a second system checks.** A couple of points costs you some
  extra reviews. `0.02` to `0.05`.
- **Something that acts on its own** — a cut-off, an alarm, a refusal. Now a point of accuracy is a
  rate of wrong actions in the field. `0.01` or tighter, and be ready for the run to fail.
- **You have no idea yet.** Start at `0.02`. If the gate passes with room to spare you learned the
  model quantizes well; if it fails you learned the opposite, and you learned it in a minute rather
  than after deployment.

What the number is *not*: a measure of whether the model is good. A model with 60% accuracy that
loses nothing to quantization passes this gate cleanly. The gate asks one question — *what did
8-bit cost?* — and `metrics.json` answers the other one.

## Why 8-bit at all

A microcontroller has a few hundred kilobytes of RAM and often no floating-point unit worth using.
A model in 32-bit floats is four times the weights and arithmetic its runtime would rather not do.
Going to 8-bit integers is what makes the model fit and run at all, so it is not an optimisation
applied at the end — it is the format, and the only question is what it cost.

Which is why the gate exists where it does. Shrinking *can* cost something, and the manifest is
where you say how much is acceptable before you find out.

A small model on cleanly separable data quantizes for free: the decisions sit far from the
boundary, so rounding the arithmetic moves the scores without changing any answer, and the gate
passes with `0.0`. That result tells you your data has margin. The gate earns its place on the data
where that is not true.

## Where to see it happen

Every {term}`run` writes `quantization.json`: the int8 model's accuracy against the trained one,
the budget, and the verdict. [Part 4 of the tutorial](../intro/tutorial04.md) makes the fit check
refuse a run on purpose, so that the first refusal you see is one you caused, and
[Choose a budget](../howto/choose-a-budget.md) is the recipe for the number.

[The budgets page](../ref/budgets.md) records what each part of Caravan has cost in dependencies and
install size, which is the project's own budget discipline rather than your model's.

:::{seealso}
{mf}`export.targets`, {mf}`output_features[].accuracy_drop_max` and
{mf}`output_features[].mae_increase_max` in the manifest reference, and the rules {rule}`F-1` and
{rule}`Q-4`.
:::
