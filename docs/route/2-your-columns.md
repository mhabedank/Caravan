# Leg 2: your own columns

:::{container} leg-head
**10 minutes.**

You will end with **a model that reads columns you chose**, and **your own accuracy figure** — not
the example's. You will have made the four decisions that every Caravan manifest comes down to.

Still nothing but your computer.
:::

Leg 1 ran somebody else's manifest. This leg writes one. You start from a small sample table, and
at the end you swap in your own file with one line.

## The four decisions

Four parts of a manifest are yours to decide. Everything else has a default.

1. **Where the data is** — `dataset`.
2. **Which columns the model reads, and what kind of thing each one is** — `input_features`.
3. **Which column it answers, and how much accuracy you will give up to make it 8-bit** —
   `output_features`.
4. **How many rows make one sample** — `preprocessing.window_size`.

## A table to work on

[`readings.csv`](../_static/data/readings.csv) holds 1,280 machine readings: a temperature, a
vibration level, the mode the machine is in (`idle` or `run`), and `state`, the column to predict:
`ok` or `fault`. It comes as twenty stretches of sixty-four readings, alternating between healthy and
faulty, with higher vibration when faulty. Download it into `data/`:

```bash
# step: own-columns
mkdir -p machine/data && cd machine
curl -L -o data/readings.csv https://mhabedank.github.io/Caravan/_static/data/readings.csv
```

One row per time step, oldest first, one header row. An empty cell is a missing reading. Your own
file takes the same shape: Caravan reads it, records its digest, and asks nothing more of it.

## The manifest

```bash
# step: own-columns
cat > manifest.yaml <<'YAML'
apiVersion: caravan/v0.2

model:
  name: machine-health
  version: 0.1.0
  template: mlp
  params:
    hidden: [16]

input_features:
  - {name: temperature, type: number}
  - {name: vibration, type: number}
  - {name: mode, type: category}

output_features:
  - name: state
    type: binary
    preprocessing: {fallback_true_label: fault}
    accuracy_drop_max: 0.02

preprocessing:
  window_size: 16
  split: {type: stratify, column: state, probabilities: [0.7, 0.15, 0.15]}

dataset: data

trainer: {epochs: 30, batch_size: 32, learning_rate: 0.001}

export:
  quantization: int8
  formats: [flatbuffer, c_array]
  targets: [esp32]
  representative_samples: 200
  test_windows: 16
YAML
```

### Why each decision went that way

**The types.** `temperature` and `vibration` are `number`, because 2 is between 1 and 3 for them.
`mode` is `category`, because `idle` and `run` are names, not quantities — and a column written as
numbers can still be a category, which is the mistake worth knowing about: a CAN identifier, a gear
position or a device id is a code, and treating it as a magnitude tells the model that id 3 is
between id 2 and id 4. [Feature types](../concepts/feature-types.md) has the rest, including what
each type does inside the model.

**The column that is not named.** Nothing reads a column you do not list. Had the table carried a
`timestamp`, leaving it out of `input_features` is all it takes; every run lists what it ignored.

**`fallback_true_label`.** `state` has exactly two values, so it is `binary`. But `ok` and `fault`
are not among the spellings Caravan recognises on its own (`yes`/`no`, `true`/`false`, `1`/`0` and
the like), and without being told it would make the one that sorts second true — `ok`, which is the
opposite of what anyone means by a fault detector. So the manifest says which one is true.

**`accuracy_drop_max: 0.02`.** Two points of accuracy is what you are willing to lose by making the
model 8-bit. This is the budget, and it is a gate rather than a warning: lose more and the run
fails and exports nothing. There is no flag to turn it off, by design.
[Budgets and gates](../concepts/budgets-and-gates.md) explains how to choose the number.

**`window_size: 16`.** Sixteen consecutive rows are one sample. Choose it from the physics — how
many time steps it takes to see the thing you want to recognise — not from the model. Windows never
overlap, and a window whose rows disagree about `state` is discarded and counted, which is why the
table above comes in stretches rather than alternating row by row. Label stretches of time, not
rows.

**The template.** `mlp` is a multilayer perceptron: dense layers over the whole window, and the
place to start. [Templates](../concepts/templates.md) says when the other template is the better
answer.

## Run it

```bash
# step: own-columns
caravan validate manifest.yaml
caravan export manifest.yaml
```

## What you have

:::{container} leg-check
Check it yourself:

```bash
# step: own-columns
run=$(ls -td runs/*/ | head -1)
python3 - "$run" <<'PY'
import json, sys
gate = json.load(open(sys.argv[1] + "quantization.json"))["gate"]
print("accuracy on the test part:", gate["trained"])
print("after making it 8-bit:    ", gate["quantized"])
print("what that cost:           ", gate["change"], "against a budget of", gate["budget"])
print("gate verdict:             ", gate["verdict"])
PY
ls "$run"model/model_data.h
```

An accuracy figure measured on data the model never trained on, the same figure after the model was
shrunk, and the gate's verdict on the difference.
:::

Those numbers are yours. They came from your columns, your window and your budget. The second one
is the one that matters: it is the model your board runs.

## Now your real table

One line. Point `dataset` at your own file or directory, list your columns with their types, name
your output column, and set the window from your own physics:

```yaml
dataset: /path/to/your/data      # a directory of .csv, .tsv or .txt files, or one file
```

Then `caravan validate manifest.yaml` and `caravan export manifest.yaml` again. Three things change
and nothing else: what you ignore, what you answer, and what you are willing to lose.

**If the gate fails on your data**, the run stops, writes a per-layer table of where the accuracy
went, and exports nothing. Leg 4 shows you a refusal on purpose. **If the run refuses your data** — a column that is not there, a window longer
than your shortest stretch, only one class present, a file with no header row — it says which rule
it is and what it found.

## Next

**[Leg 3 — onto a board](3-onto-a-board.md)** takes what you just built and runs it on a
microcontroller, then checks the board's answers against your computer's.

If you stop here, you have a manifest of your own and a model that reads your data.
