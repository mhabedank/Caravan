# Contract: the manifest `init` writes

**Feature**: 013-guided-manifest-setup

An ordinary `caravan/v0.2` manifest. Section order is the schema's. A key is written only when the
schema requires it or the author's answer differs from what would resolve without it (FR-017).

## Always written

| Key | From |
|---|---|
| `apiVersion` | `SCHEMA_VERSION` of the installed build |
| `model.name`, `model.version`, `model.template`, `model.params` | answers (`params` has required keys in every built-in template) |
| `input_features[*].name`, `.type` | answers, one flow mapping per feature, in header order |
| `output_features[0].name`, `.type`, and its budget key | answers |
| `dataset` | the data path, relative to the manifest's directory |
| `export.targets` | answers |
| `export.representative_samples` | answer (required for int8, no default) |

## Written only when needed

| Key | When |
|---|---|
| `preprocessing.window_size` | the template consumes a window (every built-in one does) |
| `output_features[0].preprocessing.normal_label` | `anomaly` output whose normal value is not `normal` |

## Never written by `init`

`defaults`, `trainer`, `random_seed`, `preprocessing.split`, `export.quantization`,
`export.formats`, `export.test_windows`, per-feature `preprocessing` and `encoder`, `loss`,
`threshold`, `clip`, `threshold_percentile`. Each keeps its documented default, which `render`
shows; an author changes one by editing the file.

## Comments

- Header: one line naming the data the manifest was set up from, one line pointing to
  the manifest reference (`docs/ref/manifest/index.md` and the site address), one line naming
  `caravan render` as the way to see every resolved value.
- One line above each top-level section saying what it is for.
- Above `input_features`: the columns left out, each with the reason from its profile
  (`# left out: dlc (8 distinct integer values — chose not to use)`), or no line when none is.

## Example (synthetic fixture, every proposal accepted, output `label`)

```yaml
# Set up by caravan init from ../tests/fixtures/datasets/synthetic.
# Every field: docs/ref/manifest/index.md · every resolved value: caravan render <this file>
apiVersion: caravan/v0.2

# What is built, and from which template.
model:
  name: synthetic-mlp
  version: 0.1.0
  template: mlp
  params:
    hidden: [32, 16]
    dropout: 0.1

# The columns the model reads, one feature each.
input_features:
  - {name: can_id, type: category}
  - {name: dlc, type: category}
  - {name: b0, type: number}
  - {name: b1, type: number}
  - {name: b2, type: number}

# The column the model answers, and what int8 may cost it.
output_features:
  - name: label
    type: category
    accuracy_drop_max: 0.02

# How many consecutive records form one sample.
preprocessing:
  window_size: 64

# The data, relative to this file.
dataset: ../tests/fixtures/datasets/synthetic

# The boards it must fit, and the samples int8 calibrates on.
export:
  targets: [s32k144]
  representative_samples: 100
```

There is no date or version stamp in the file: anything not derived from the answers would break
FR-020's byte-identical guarantee, and version control already records when a file was written.
