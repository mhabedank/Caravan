# Leg 1: your first model

:::{container} leg-head
**5 minutes.**

You will end with an **int8 model and its C array on disk**, and a run report that says what
shrinking the model cost in accuracy. You will have seen the gate pass.

Nothing but your computer. No board yet.
:::

## Before the first command

**Python 3.13.** Training runs on Python 3.13. On 3.14 or 3.15, `validate` and `render` work and
`export` stops with a message naming the version it needs, before it writes anything.

**A POSIX shell.** Use Linux, macOS, or WSL on Windows.

## Install

The download is 2 GB, nearly all of it the training framework. Start it and read on.

The `.` line activates the environment, and every later command runs inside it. If `pip` complains
that your Python is too old, the environment is not active — run `deactivate` and the `.` line
again.

```bash
# step: install
python3.13 -m venv caravan-try
. caravan-try/bin/activate
pip install "caravan-ml[train,verify] @ https://github.com/mhabedank/Caravan/releases/download/v0.1.0rc3/caravan_ml-0.1.0rc3-py3-none-any.whl"
caravan --version
```

`caravan --version` prints `caravan-ml 0.1.0rc3`.

## Fetch the worked example

Two directories out of the tagged source: the example manifest and the synthetic data it reads. No
`git` needed.

```bash
# step: fetch
curl -sL https://github.com/mhabedank/Caravan/archive/refs/tags/v0.1.0rc3.tar.gz \
  | tar xz --strip-components=1 Caravan-0.1.0rc3/examples Caravan-0.1.0rc3/tests/fixtures/datasets/synthetic
```

Leg 1 uses the example's own data. It finishes in under a minute. Your own table is leg 2.

## Run it

```bash
# step: run
caravan validate examples/picket-mlp.yaml
caravan render examples/picket-mlp.yaml --stdout
caravan export examples/picket-mlp.yaml
```

Three commands, and each one answers a different question.

**`validate`** asks whether the manifest is well formed, and says `valid`. It reads no data, so it
is instant and it is what you run after every edit.

**`render`** shows you the manifest the pipeline will actually use, with every default filled in:
each column's preprocessing, the trainer's settings, how the data is split. Anything it prints as
`derived` is something only the data can say — the order of the labels, the vocabulary of a text
column, the size of an embedding — and it is filled in when the data is read.

**`export`** runs everything: it reads the data, splits it, learns each column's preprocessing from
the training part, builds the model with that preprocessing inside it, checks the model against the
boards before spending time on training, trains, shrinks to int8, measures what the shrinking cost,
and writes the files. Run it again and every stage comes from the cache.

The last lines name the run directory, `runs/<time>-<digest>/`.

## What you have

:::{container} leg-check
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

Two files and a verdict. `model.tflite` is the int8 model; `model_data.h` is the same model as a C
array your firmware can compile.

Everything the gate decided is in one place, `quantization.json`, under `gate`: what the trained
model scored, what the int8 model scored, the difference, the budget it was compared against, and
the verdict. The example's model loses nothing at all, so `cost` is `0.0` against a budget of
`0.02`.
:::

That is the whole point of this leg. The model exists, it is 8-bit, and you know what being 8-bit
cost it — because the run measured the shrunken model against the trained one and compared the
difference with the budget the manifest set.

The run directory holds more than those two files, and
[what a run leaves](../concepts/what-a-run-leaves.md) explains each one at the point you need it.
The two that matter next are `model/interface.json`, which says what your firmware must pass and in
what order, and `report.json`, which is the whole run written down.

## If the gate had failed

On the example it passes. On your own data it can fail: the run stops, writes a per-layer table of
where the accuracy went, and exports nothing.
[Budgets and gates](../concepts/budgets-and-gates.md) explains what it measures, and leg 4 makes it
happen on purpose so you have seen it before it matters.

## Next

**[Leg 2 — your own columns](2-your-columns.md)** points the same pipeline at a table of yours. It
is the leg where the numbers become yours.

If you stop here, you have a working install and a worked example you can re-run and edit.
