# Quickstart: Validating Build and Train

Date: 2026-10-22 · Feature: 002

Runnable scenarios that prove the feature works. Each one maps to a success criterion of
[spec.md](./spec.md). Details live in the contracts; this is the run guide.

## Prerequisites

```bash
# The core, on any supported Python (3.13, 3.14 or 3.15)
uv sync

# The training extra — Python 3.13 only, see research R1
uv venv --python 3.13 .venv313
uv pip install --python .venv313 -e ".[train]"
```

On 3.14 or 3.15 the extra installs Caravan's training code and no framework, which is the point of
scenario 5.

## 1 — Build the pilot model (SC-002, and FR-003's shape report)

```bash
caravan build tests/fixtures/manifests/valid/picket-mlp-fixture.yaml
```

Expect: exit 0; the shape line of the CLI contract on standard error; a new run directory holding
`model/built.keras` and `model/built.json`; `built.json` reporting input shape `[64, 5]`, output 4,
and a parameter count that matches the layer table.

## 2 — Train it end to end (SC-001, SC-002, SC-003)

```bash
time caravan train tests/fixtures/manifests/valid/picket-mlp-fixture.yaml
```

Expect: exit 0 in under 60 seconds including the framework's import; the run directory holding
`model/trained.keras`, both checkpoints, `metrics.json` and `training-history.json`; and every entry
in `metrics.json` carrying `split`, `dataset_version` and `samples`. Check the last part directly:

```bash
jq '[.metrics[] | select(.split == null or .dataset_version == null or .samples == null)] | length' \
  runs/*/report.json   # must be 0
```

## 3 — Editing compliance text retrains nothing (SC-004)

```bash
caravan train manifest.yaml                      # produces
sed -i 's/intended_use: .*/intended_use: "edited"/' manifest.yaml
caravan train manifest.yaml                      # reuses
jq '.stages[] | {name, outcome}' runs/*/report.json | tail -4
```

Expect: both stages `reused` on the second run, and a wall-clock difference that makes it obvious no
training happened.

## 4 — The four things that must retrain (SC-005)

Change each of these in turn and expect `outcome: "produced"` for `train`:

| Change | Why it must retrain |
|---|---|
| `model.params.hidden` | a different model |
| `train.seed` | a different initialisation and split |
| `train.learning_rate` | a different optimisation |
| a byte of the dataset | different data |

And expect `build` to stay `reused` for the seed and the learning rate, because neither is in
`build.reads`.

## 5 — No framework installed (SC-006)

```bash
uv run --python 3.14 --no-project caravan build picket-mlp.yaml ; echo "exit: $?"
```

Expect: exit 4; the window-and-reason message of the CLI contract; no traceback anywhere in the
output; and no run directory left behind.

## 6 — The core still loads no framework (SC-007)

```bash
uv run pytest tests/layering -q
uv run python -c "import sys, caravan.manifest.load, caravan.stages.train, caravan.templates.registry; \
print([m for m in sys.modules if m.split('.')[0] in {'tensorflow','keras','numpy'}])"
```

Expect: the layering tests pass on every Python in the matrix, and the printed list is empty — note
that `caravan.stages.train` is among the imports, because importing a stage must not import what the
stage loads by name.

## 7 — A dataset that disagrees with its manifest (SC-008)

```bash
uv run pytest tests/unit/test_dataset_rules.py -q
```

One fixture per DS rule, each asserting the rejection names both sides. Expect every DS rule in the
data model to have a fixture; the coverage test fails when one does not, exactly as it does for the
manifest rules of feature 001.

## 8 — The repository carries no dataset but the fixture (SC-009, SC-010)

```bash
uv run pytest tests/unit/test_fixture_dataset.py -q
du -sh tests/fixtures/datasets/synthetic
```

Expect: the fixture regenerates byte-identically from its committed `make.py`; the directory is
under 200 KB; and a run over it reports `windows_discarded_mixed` of at least 1, which is the
boundary window the fixture contains on purpose.
