# Leg 1: your first model

:::{container} leg-head
**About 5 minutes**, once the install has finished.

You will end with an **int8 model and its C array on disk**, and a run report that says what
shrinking the model cost in accuracy. You will have seen the gate pass.

Nothing but your computer. No board yet.
:::

## Before the first command: two things that will stop you

**Python 3.13, and only 3.13.** Training needs exactly this version — the training framework
publishes nothing newer yet. Checking and previewing a manifest work on 3.13, 3.14 and 3.15, so if
you are on 3.14 or 3.15 you can follow this leg as far as `render` and then stop; the commands that
train say which version they need and exit without writing anything.

**Linux or macOS.** These commands are written for a POSIX shell. On Windows they work under WSL.
Nothing here has been tested in PowerShell, so if that is where you are, start WSL first.

## Install

About 2 GB of download, nearly all of it the training framework. Start it now and read on.

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

Leg 1 uses the example's own data on purpose. A known table finishes in under a minute, which is
what makes this leg five minutes instead of an afternoon. Your own table is leg 2.

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
and writes the files. Under a minute on a laptop. Run it again and every stage comes from the cache.

The last lines name the run directory, `runs/<time>-<digest>/`.

## What you have

:::{container} leg-check
Check it yourself:

```bash
run=$(ls -td runs/*/ | head -1)
ls "$run"model/model.tflite "$run"model/model_data.h
python3 -c "import json,sys; q=json.load(open(sys.argv[1])); print('verdict:', q['verdict']); print('accuracy cost:', q.get('accuracy_drop'))" "$run"quantization.json
```

Two files and a verdict. `model.tflite` is the int8 model; `model_data.h` is the same model as a C
array your firmware can compile. The verdict is the gate's answer.
:::

That is the whole point of this leg. The model exists, it is 8-bit, and you know what being 8-bit
cost it — because the run measured the shrunken model against the trained one and compared the
difference with the budget the manifest set.

The run directory holds more than those two files, and
[what a run leaves](../concepts/what-a-run-leaves.md) explains each one at the point you need it.
The two that matter next are `model/interface.json`, which says what your firmware must pass and in
what order, and `report.json`, which is the whole run written down.

## If the gate had failed

It does not fail on the example, because the example's budget and data are known to each other. On
your own data it can, and that is a correct outcome rather than a bug: the run stops, writes a
per-layer table of where the accuracy went, and exports nothing.
[Budgets and gates](../concepts/budgets-and-gates.md) explains what it measures, and leg 4 makes it
happen on purpose so you have seen it before it matters.

## Next

**[Leg 2 — your own columns](2-your-columns.md)** points the same pipeline at a table of yours. It
is the leg where the numbers become yours, and it is about ten minutes.

If you stop here, you have a working install and a worked example you can re-run and edit. Nothing
in this leg has to be undone.
