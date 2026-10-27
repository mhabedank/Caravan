# Leg 4: when it does not fit

:::{container} leg-head
**About 5 minutes**, after the half hour. This leg is not part of the thirty-minute promise on
purpose.

You will end with **a check you made refuse on purpose**, the numbers it printed read and
understood, and a clear idea of **which of Caravan's two gates you will meet first**.

Your computer only. No board, and no training — the refusal happens before training starts.
:::

Everything so far worked. That is the problem with it: the one thing Caravan will not let you skip
is the thing you have not seen yet. A gate you meet for the first time on a Friday afternoon, with a
deadline, on data you do not know, is a bad introduction. So let us cause one now, on data that does
not matter.

This leg continues from [leg 2](2-your-columns.md) — the `machine/` directory and its manifest.

## Make it refuse

One edit: ask for a model far too big for the board you named.

```bash
# step: tighten
cd machine
cp manifest.yaml manifest.yaml.bak
sed -i 's/hidden: \[16\]/hidden: [4096, 4096]/' manifest.yaml
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

Read that message closely, because three things in it are the design.

**"before any training".** The run stopped in seconds. It did not train for an hour and then tell
you. The fit check runs after the model is built and before training starts, precisely so that the
answer arrives while it is still cheap.

**"a floor is a lower bound, so no training can make this model fit".** This is why the check is
allowed to be certain. It compares what the weights *must* occupy against what the board *has* —
17 MB against 4 MB — and no amount of training changes the number of weights. A model it stops
cannot fit, and that is a fact rather than an estimate.

**"short by 12,881,938".** It tells you the size of your problem. Twelve megabytes short is not a
tuning question; it is the wrong architecture for this board. Shortening it to `[64]` is the answer,
not nudging `[4096, 4096]`.

:::{container} leg-check
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
deploy by accident. The run directory holds the report, the resolved manifest and what the data
stage learned — enough to see what happened — and no artifact.

## Put it back

```bash
# step: tighten
mv manifest.yaml.bak manifest.yaml
caravan export manifest.yaml
cd ..
```

## The other gate, and why you did not see it fail

Caravan has two checks that stop a run, and you have now met one. The other is the **quantization
gate**, and on this model you cannot make it fail — which is worth knowing rather than hiding.

Look at what leg 2 printed: `what that cost: 0.0 against a budget of 0.02`. Making this model 8-bit
cost it **nothing at all**. Set the budget to zero and the run still passes, because zero loss is
within a zero budget.

That is not a trick of the example. A small model on cleanly separable data often quantizes for
free: the decisions sit far from the boundary, so rounding the arithmetic to 8-bit integers moves
the scores without changing any answer. **The gate has nothing to stop because there is nothing
wrong.**

You will meet it for real when your data is harder — classes that overlap, a model whose decisions
sit near the boundary, or a `number` output where every rounding shows up in the error. Then the
budget starts refusing runs, and what it emits is the thing to look for:

- the same `gate` record in `quantization.json`, with `verdict: fail`;
- a **per-layer table** in `quantization-error.csv`, naming which layer turned 8-bit worst.

That table is the point of failing rather than warning. A verdict tells you that you have a problem;
the table tells you which layer to change.

## Choosing the budget, now that you have seen both

The question is not "what will pass" — that is how you get a budget that means nothing. It is
**what happens when this model is wrong**:

- **A human or a second system checks every answer.** A couple of points of accuracy costs some
  extra reviews. `0.02` to `0.05` is honest.
- **It acts on its own** — a cut-off, an alarm, a refusal. Now a point of accuracy is a rate of
  wrong actions out in the world. `0.01` or tighter, and expect refusals.
- **You do not know yet.** `0.02`, and let the first run tell you whether this model quantizes well.
  If it costs `0.0`, as here, you have learned something useful about your data.

Write the number in the manifest and the reason in a comment beside it. The number is a product
decision living in a modelling file, and in six months the comment is the only thing that will
explain it.

And note what neither gate asks: **whether the model is any good.** A model with 60% accuracy that
loses nothing to quantization passes both checks cleanly. `metrics.json` answers that question, and
the gates answer a different one — *does what you deploy behave like what you trained, and does it
fit?*

## The end of the route

You have built a model, made it read your own data, run it on hardware, checked the hardware against
your computer, and made a check refuse and say why.

Where to go next depends on what you want:

- **Every field, with its defaults and its reasons** — [the manifest reference](../reference/manifest.md).
- **Every command** — [the CLI reference](../reference/cli.md).
- **Both gates in full** — [budgets and gates](../concepts/budgets-and-gates.md).
- **What is actually verified, and how far** — [compatibility](../compatibility.md).
