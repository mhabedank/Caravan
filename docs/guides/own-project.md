# Your own project

From a CSV of your own to a model on a board. Each step names one decision and links its entry in
the [manifest reference](../reference/manifest.md). The example is a small machine-monitoring
dataset: is the machine in fault, from its temperature, its vibration, its mode and whether its
door is open.

You need Caravan installed with both extras ([Try it](../try-it.md)).

## 1. Lay out the data

`dataset` points at a directory of `.csv` files (or `.tsv`, `.txt`), or at one file.
- **The files:** they are read in path order as one sequence of records. Each has the same header
  row.
- **The rows:** one row per time step, oldest first.
- **Missing readings:** an empty cell is a missing reading.

```text
machine/
├── manifest.yaml
└── data/
    ├── 2026-10-01.csv
    └── 2026-10-02.csv
```

```text
timestamp,temperature,vibration,mode,door,state
2026-10-01T08:00:00,41.2,0.18,idle,closed,ok
2026-10-01T08:00:01,41.3,0.21,idle,closed,ok
...
```

Your data stays yours: Caravan reads it and records its digest, nothing more. Keep it out of any
repository you publish.

## 2. Choose a type for each column the model reads

Each column the model reads is an input feature: a `name` and a [type](../reference/manifest.md#input_features).
Every other column is ignored, and each run lists it under `ignored_columns`. Here that is
`timestamp`.

| Column | What it is | Type |
|---|---|---|
| `temperature` | a measurement | `number` |
| `vibration` | a measurement | `number` |
| `mode` | one of a few names (`idle`, `run`, `clean`) | `category` |
| `door` | one of two states | `binary` |

**The rule of thumb:**
- **`number`:** a quantity, where 2 is between 1 and 3.
- **`category`:** a code or a name, where 2 is not between 1 and 3. That includes CAN
  identifiers, gear positions and device ids, even when they are written as numbers.
- **`binary`:** exactly two states.

`door` is spelt `open` and `closed`, which are not among Ludwig's standard spellings (`yes`/`no`,
`true`/`false`, `1`/`0`, …). So the manifest says which one means true:
`preprocessing: {fallback_true_label: open}`.

## 3. Choose the output and its budget

The column the model answers is the one output feature.
- **`category`:** one of several classes.
- **`binary`:** yes or no.
- **`number`:** a value.

Here `state` is `ok` or `fault`, so `binary`, with `fault` as true.

**The budget** says how much int8 quantization may cost on the test part:
- **for a category or binary:** `accuracy_drop_max`, here 0.05;
- **for a number:** `mae_increase_max`, in the column's unit.

A run that quantization makes worse than that fails, and leaves no model to export
([budgets](../budgets.md)).

## 4. Choose the window

`preprocessing.window_size` consecutive rows form one sample. Choose it from the physics: how many
time steps show what you want to recognise.
- **The size here:** 16 rows.
- **Overlap:** windows never overlap.
- **Mixed windows:** a window whose rows disagree on `state` is discarded and counted.

So label each stretch of time, not each row.

## 5. Choose the split

The windows are split into training, validation and test parts.
- **`stratify`:** keeps the share of each class equal across the parts. Here it is used with the
  default `[0.7, 0.15, 0.15]`.
- **`fixed`:** use it when windows of one machine, vehicle, person or recording must not appear on
  both sides. Add a column that names each row's part (`train`, `validation`, `test`) and use
  `split: {type: fixed, column: <that column>}`.

  Use `fixed` too when your recording was cut into overlapping pieces before Caravan saw it.
  Otherwise the test part would contain near-copies of training data, and every number would be
  too good.

Every statistic, such as a mean or a vocabulary, is fitted on the training part only.

## 6. Choose the template

- **`mlp`:** dense layers over the whole window. Start here: `hidden: [16]`, wider or deeper if the
  model underfits.
- **`conv1d`:** convolutions along time, for signals where the shape of a pattern matters more
  than where it is in the window: vibration, motion, audio-like data.

## 7. Choose the boards

`export.targets` names the boards the model must fit (`caravan boards`).
- **Before training:** `build` checks the model against each board's flash and RAM.
- **For the board guide:** include `esp32`.
- **`export.test_windows`:** writes windows of the test part with the answers your computer gave,
  for the board to compare against.

## The manifest

```yaml
# example: own-project
apiVersion: caravan/v0.2

model:
  name: machine-state
  version: 0.1.0
  template: mlp
  params:
    hidden: [16]

input_features:
  - {name: temperature, type: number}
  - {name: vibration, type: number}
  - {name: mode, type: category}
  - name: door
    type: binary
    preprocessing: {fallback_true_label: open}

output_features:
  - name: state
    type: binary
    preprocessing: {fallback_true_label: fault}
    accuracy_drop_max: 0.05

preprocessing:
  window_size: 16
  split: {type: stratify}

dataset: data/

trainer: {epochs: 40, batch_size: 16, learning_rate: 0.003}
random_seed: 42

export:
  targets: [esp32]
  representative_samples: 100
  test_windows: 8
```

## 8. Run it

```bash
caravan validate manifest.yaml
caravan render manifest.yaml --stdout
caravan export manifest.yaml
```

What each command does:
1. **`validate`** checks the manifest without reading the data. Each finding names its
   [rule](../reference/rules.md), the field and what is accepted.
2. **`render`** shows every default filled in.
3. **`export`** reads the data, trains, quantizes, checks the budget and writes the files.

## 9. Read the result

In the run directory (`runs/<time>-<digest>/`):
- **`report.json`:** the run, every stage, and the gate's verdict.
- **`data/schema.json`:** which columns were used and ignored, and how many windows each part got.
- **`quantization.json`:** the accuracy before and after int8, and the budget.
- **`export.json`:** the size, the operators, and which ones the ESP32 accelerates.

If the gate fails, the run has written a per-layer error table that shows where accuracy was lost.

## 10. Onto the board

Follow [On the board: LILYGO LoRa32](lora32.md). Your run's four files take the place of the
example's. Nothing else changes.
