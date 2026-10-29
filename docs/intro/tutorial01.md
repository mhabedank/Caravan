# Part 1: Your first model

:::{admonition} You will learn
:class: learn
**5 minutes**, with Caravan [installed](install.md). Nothing but your computer.

- how to fetch the worked example and run it with three commands;
- what {cmd}`caravan validate`, {cmd}`caravan render` and {cmd}`caravan export` each answer;
- where a run puts its files, and which of them your firmware compiles;
- how to read the verdict of the {term}`quantization gate`.

You end with an **int8 model and its C array on disk**, and a run report that says what shrinking
the model cost in accuracy.
:::

## Fetch the worked example

Two directories out of the tagged source: the example {term}`manifest` and the synthetic data it
reads. No `git` needed.

```bash
# step: fetch
curl -sL https://github.com/mhabedank/Caravan/archive/refs/tags/v0.1.0rc3.tar.gz \
  | tar xz --strip-components=1 Caravan-0.1.0rc3/examples Caravan-0.1.0rc3/tests/fixtures/datasets/synthetic
```

Part 1 uses the example's own data, and its export finishes in under a minute. Your own table is
part 2.

## Run it

```bash
# step: run
caravan validate examples/picket-mlp.yaml
caravan render examples/picket-mlp.yaml --stdout
caravan export examples/picket-mlp.yaml
```

Three commands, and each one answers a different question.

**{cmd}`caravan validate`** asks whether the {term}`manifest` is well formed, and says `valid`. It
reads no data, so it is instant, and it is what you run after every edit.

**{cmd}`caravan render`** shows the manifest the pipeline will use, with every default filled in:
each column's preprocessing, the trainer's settings, how the data is split. Anything it prints as
{term}`derived` is something only the data can say — the order of the labels, the
{term}`vocabulary` of a text column, the size of an embedding — and it is filled in when the data
is read.

**{cmd}`caravan export`** runs every {term}`stage`: it reads the data, splits it, learns each
column's preprocessing from the {term}`training part`, builds the model with that preprocessing
inside it, checks the model against the boards before training, trains, shrinks it to
{term}`int8`, measures what the shrinking cost, and writes the files. Run it again and every stage
comes from the cache. [The pipeline](../topics/pipeline.md) explains the five stages and what each
one leaves.

The last lines name the run directory, `runs/<time>-<digest>/`.

## What you have

:::{container} tutorial-check
Check it yourself:

```bash
# step: check
run=$(ls -td runs/*/ | head -1)
ls "$run"model/model.tflite "$run"model/model_data.h
python3 - "$run" <<'PY'
import json, sys
gate = json.load(open(sys.argv[1] + "quantization.json"))["gate"]
print(f"measured on the {gate['split']} part, {gate['samples']} samples")
print(f"trained model:   {gate['trained']}")
print(f"int8 model:      {gate['quantized']}")
print(f"{gate['metric']} cost: {gate['change']}, budget {gate['budget']}")
print(f"verdict:         {gate['verdict']}")
PY
```

Two files and a verdict. `model.tflite` is the int8 model; `model_data.h` is the same model as a
{term}`C array` your firmware compiles.

Everything the {term}`gate` decided is in one place, `quantization.json`, under `gate`: what the
trained model scored, what the int8 model scored, the difference, the {term}`budget` it was
compared against, and the verdict. The example's model loses nothing, so `cost` is `0.0` against a
budget of `0.02`.
:::

That is what part 1 is for. The model exists, it is 8-bit, and you know what being 8-bit cost it,
because the run measured the shrunken model against the trained one and compared the difference
with the budget the manifest set.

The run directory holds more than those two files, and
[what a run leaves](../topics/what-a-run-leaves.md) explains each one. The two you need next are
`model/interface.json`, the {term}`interface contract` that says what your firmware passes and in
what order, and `report.json`, the {term}`run report`.

## When the gate fails

On the example the {term}`gate` passes. On your own data it can fail: the run stops, writes a
per-layer table of where the accuracy went, and exports nothing.
[Budgets and gates](../topics/budgets-and-gates.md) explains what it measures, and
[part 4](tutorial04.md) makes a check refuse on purpose.

## Next

[Part 2](tutorial02.md) points the same pipeline at a table of yours, and the numbers become yours.
You already have a working install and a worked example you can re-run and edit.
