# Leg 4: when it does not fit

:::{container} leg-head
**About 10 minutes**, after the half hour. This leg is not part of the thirty-minute promise on
purpose.

You will end with **a failed gate you caused**, the **per-layer table** it printed read and
understood, and **a budget you chose** rather than copied.

Your computer only. No board needed.
:::

Everything so far worked. That is the problem with it: the one thing Caravan will not let you skip
is the thing you have not seen yet. A gate you meet for the first time on a Friday afternoon, with
a deadline, on data you do not know well, is a bad introduction. So let us break it now, on purpose,
on data that does not matter.

This leg continues from [leg 2](2-your-columns.md) — the `machine/` directory and its manifest.

## Make it refuse

One edit. Set the budget to something no model can meet:

```bash
# step: tighten
cd machine
sed -i.bak 's/accuracy_drop_max: 0.02/accuracy_drop_max: 0.0/' manifest.yaml
caravan export manifest.yaml || echo "exit code: $?"
```

`accuracy_drop_max: 0.0` says: *making this model 8-bit may cost nothing at all.* Shrinking always
costs something, so this cannot pass, and it is the cheapest way to see what failing looks like.

## What it did

The run **failed**, with a non-zero exit code, and **exported nothing**. Not a warning, not an
export with a note attached. There is no flag that would have let it through, and that is the whole
design: a check you can silence becomes a check that is always silenced.

:::{container} leg-check
Read what it left behind:

```bash
# step: tighten
run=$(ls -td runs/*/ | head -1)
python3 -c "
import json, sys
q = json.load(open(sys.argv[1] + 'quantization.json'))
print('verdict:  ', q['verdict'])
print('budget:   ', q.get('accuracy_drop_max'))
print('cost:     ', q.get('accuracy_drop'))
for layer in (q.get('per_layer') or q.get('layers') or [])[:5]:
    print('  ', layer)
" "$run"
```
:::

Three things are in there, and the third is the one that matters.

**The verdict** says it failed. That you knew.

**The budget and the cost** say by how much. Useful.

**The per-layer table** says *where the accuracy went* — which layer turned 8-bit worst. That is
the only part you can act on. A verdict tells you that you have a problem; the table tells you
which layer to change. This is why a failed gate emits it rather than just refusing.

## Now choose a budget

Put it back, but choose the number this time rather than inheriting it:

```bash
# step: tighten
mv manifest.yaml.bak manifest.yaml
caravan export manifest.yaml
cd ..
```

The question to ask is not "what will pass" — that is how you end up with a budget that means
nothing. It is **what happens when this model is wrong**:

- **A human or a second system checks every answer.** A couple of points of accuracy costs you some
  extra reviews. `0.02` to `0.05` is honest.
- **It acts on its own** — a cut-off, an alarm, a refusal. Now a point of accuracy is a rate of
  wrong actions out in the world. `0.01` or tighter, and expect the run to fail sometimes. That is
  the gate doing its job.
- **You do not know yet.** `0.02`, and let the first run tell you whether this model quantizes well.

Write the number down in the manifest and the reason in a comment. The number is a product decision
living in a modelling file, and six months later the comment is the only thing that will explain it.

## What this does not measure

The gate asks one question: *what did 8-bit cost?* It does not ask whether the model is any good.

A model with 60% accuracy that loses nothing to quantization passes this gate cleanly. That is not
a bug — `metrics.json` is where you look for whether the model works at all, and the two questions
are separate on purpose. Passing the gate means the model you deploy behaves like the model you
trained. It does not mean the model you trained was worth deploying.

## The other gate

There is a second check, and it runs earlier: before training, the build stage compares the model
against every board in `export.targets` and fails if it cannot possibly fit. You are unlikely to
trip it with `hidden: [16]`, but you will the first time you try a wide model on a small part, and
it fails in seconds rather than after an hour of training.

[Budgets and gates](../concepts/budgets-and-gates.md) explains both checks, including the thing
worth knowing about the early one: a model it *stops* cannot fit, but a model it *passes* might
still not — its figures are <span class="prov estimated">estimated</span> lower bounds, and the real
answer comes from the board.

## The end of the route

You have built a model, made it read your own data, run it on hardware, checked the hardware against
your computer, and seen the gate refuse a run and say why.

Where to go next depends on what you want:

- **Every field, with its defaults and its reasons** — [the manifest reference](../reference/manifest.md).
- **Every command** — [the CLI reference](../reference/cli.md).
- **What is actually verified, and how far** — [compatibility](../compatibility.md).
- **What is planned, and what was decided against** — [the roadmap](../roadmap.md).
