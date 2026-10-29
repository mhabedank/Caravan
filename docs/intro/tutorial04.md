# Part 4: When it does not fit

:::{admonition} You will learn
:class: learn
Your computer only, no board, and no training: the refusal happens before training starts.

- how to make the {term}`fit check` refuse a run, and how to read what it prints;
- why a refusal leaves nothing to deploy;
- when the {term}`quantization gate` refuses instead, and what it writes;
- how to choose a {term}`budget` for your own model.

You end with **a check you made refuse on purpose**, and you know **which of Caravan's two gates
you will meet first**.
:::

Everything so far worked. The one thing Caravan will not let you skip is the thing you have not seen
yet. So cause a refusal now, on data that does not matter.

This part continues from [part 2](tutorial02.md): the `machine/` directory and its manifest.

## Make it refuse

One edit: ask for a model far too big for the board you named.

```bash
# step: tighten
cd machine
sed -i.bak 's/hidden: \[16\]/hidden: [4096, 4096]/' manifest.yaml
caravan export manifest.yaml || echo "exit code: $?"
```

Two layers of 4,096 units instead of one of 16. Nothing else changes.

## What it did

```text
export.targets — the built model cannot fit 1 target board before any training: a floor is a
lower bound, so no training can make this model fit that board, found
['esp32 flash: the floor is 17,076,242 bytes and the board has 4,194,304 (short by 12,881,938)']
stage fit failed
```

The message is reported at {mf}`export.targets` under rule {rule}`F-1`, and three things in it are
the design.

**"before any training".** The run stopped in seconds. The {term}`fit check` runs after the model is
built and before training starts, so the answer arrives while it is still cheap.

**"a floor is a lower bound, so no training can make this model fit".** This is why the check can
be certain. It compares what the weights *must* occupy against what the {term}`board` *has* — 17 MB
against 4 MB — and no amount of training changes the number of weights. A model it stops cannot
fit.

**"short by 12,881,938".** It tells you the size of your problem. Twelve megabytes short is not a
tuning question; it is the wrong architecture for this board. Shrinking it to `[64]` is the answer,
not nudging `[4096, 4096]`.

:::{container} tutorial-check
Check it yourself:

```bash
# step: tighten
run=$(ls -td runs/*/ | head -1)
python3 - "$run" <<'PY'
import json, sys
report = json.load(open(sys.argv[1] + "report.json"))
print("outcome:", report["outcome"])
for finding in report["findings"]:
    print("rule:   ", finding["rule"], "at", finding["path"])
    for item in finding["found"]:
        print("   ", item)
PY
ls "$run"model/model.tflite 2>/dev/null || echo "model/model.tflite: never written, which is the point"
```
:::

**No model was written.** The failure is not a warning with an export attached; there is nothing to
deploy by accident. The run directory holds the {term}`run report`, the resolved manifest and what
the data stage learned, and no artifact.

## Put it back

```bash
# step: tighten
mv manifest.yaml.bak manifest.yaml
caravan export manifest.yaml
cd ..
```

## The other gate

Caravan has two checks that stop a run, and you have now met one. The other is the
{term}`quantization gate`, and on this model it cannot fail.

Part 2 printed `what that cost: 0.0 against a budget of 0.02`. Making this model 8-bit cost it
**nothing**. Set the budget to zero and the run still passes, because zero loss is within a zero
budget.

A small model on cleanly separable data quantizes for free: the decisions sit far from the
boundary, so rounding to 8-bit integers moves the scores without changing any answer. **The gate
has nothing to stop because nothing is wrong.**

You meet it when your data is harder: classes that overlap, decisions near the boundary, or a
`number` output where every rounding shows up in the error. Then the budget refuses runs, under
rule {rule}`Q-4`, and writes:

- the same `gate` record in `quantization.json`, with `verdict: fail`;
- a **per-layer table** in `quantization-error.csv`, naming which layer turned 8-bit worst.

That table is the reason for failing rather than warning. A verdict tells you that you have a
problem; the table tells you which layer to change.

## Choosing the budget

The question is not "what will pass" — that gives a {term}`budget` that means nothing. It is
**what happens when this model is wrong**:

- **A human or a second system checks every answer.** A couple of points of accuracy costs some
  extra reviews. `0.02` to `0.05`.
- **It acts on its own** — a cut-off, an alarm, a refusal. Now a point of accuracy is a rate of
  wrong actions out in the world. `0.01` or tighter, and expect refusals.
- **You do not know yet.** Start at `0.02` and read the first run's cost. A cost of `0.0`, as here,
  tells you the model quantizes cleanly.

Write the number in the manifest and the reason in a comment beside it. The number is a product
decision living in a modelling file, and in six months the comment is what explains it.
[Choose a budget](../howto/choose-a-budget.md) is the recipe.

Neither gate asks **whether the model is any good.** A model with 60% accuracy that loses nothing
to quantization passes both checks. `metrics.json` answers that question; the gates answer a
different one — *does what you deploy behave like what you trained, and does it fit?*

## The end of the tutorial

You have built a model, made it read your own data, run it on hardware, checked the hardware against
your computer, and made a check refuse and say why.

Where to go next:

- **Every field, with its defaults and its reasons** — [the manifest reference](../ref/manifest/index.md).
- **Every command** — [the CLI reference](../ref/cli.md).
- **Both gates in full** — [budgets and gates](../topics/budgets-and-gates.md).
- **What is verified, and how far** — [what is verified today](../ref/compatibility.md).
- **Everything else** — [the documentation contents](../contents.md).
