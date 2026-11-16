# Quickstart: validating `caravan init`

**Feature**: 013-guided-manifest-setup

Runnable checks that prove the feature end to end. Each names the requirement or criterion it
covers. The command options are in [contracts/cli-init.md](contracts/cli-init.md); the written file
is described in [contracts/manifest-output.md](contracts/manifest-output.md).

## Prerequisites

A checkout with the **default installation only** — no `train` or `verify` extra — on any supported
Python (3.13, 3.14, 3.15). That is itself a check of FR-023.

```bash
pip install -e .
```

Work in a scratch directory beside the repository, so the relative data paths below hold:

```bash
mkdir -p scratch && cd scratch
```

## 1. The dialogue, every proposal accepted (US1, SC-001, SC-003)

```bash
caravan init
```

Type `../tests/fixtures/datasets/synthetic` at the first question, then press Enter at every other
question, the summary included.

Expected:
- the column list shows `can_id` proposed as `category` with the identifier reason, `dlc` as
  `category` with "8 distinct integer values", `b0`–`b2` as `number`;
- `label` is proposed as the output, as a `category`;
- at most 12 answers in total;
- the last lines read `wrote synthetic-mlp.yaml — valid` and `next: caravan build synthetic-mlp.yaml`.

```bash
caravan validate synthetic-mlp.yaml --no-report   # exit 0
caravan render synthetic-mlp.yaml --stdout        # every feature with its resolved settings
```

## 2. The same answers piped in, and without questions (US3, FR-020, FR-021, FR-022)

```bash
{ echo ../tests/fixtures/datasets/synthetic; yes ''; } | caravan init piped.yaml
caravan init quiet.yaml --no-input --dataset ../tests/fixtures/datasets/synthetic
cmp piped.yaml quiet.yaml
cmp piped.yaml synthetic-mlp.yaml
```

Every empty line accepts a proposal, the summary's included. Both `cmp` print nothing: the three
files are byte-identical.

## 3. A missing answer without a proposal (US3 scenario 2)

```bash
caravan init --no-input; echo "exit $?"
```

Expected: exit 2, and the message names `--dataset` as the missing answer.

## 4. Never overwrite silently (FR-004)

```bash
caravan init quiet.yaml --no-input --dataset ../tests/fixtures/datasets/synthetic; echo "exit $?"
caravan init quiet.yaml --no-input --dataset ../tests/fixtures/datasets/synthetic --overwrite; echo "exit $?"
```

Expected: exit 2 with "exists" and `--overwrite` named; then exit 0.

## 5. An anomaly model and an output type that needs another template (FR-009, FR-010)

```bash
caravan init ae.yaml --no-input --dataset ../tests/fixtures/datasets/anomaly --output-type anomaly
grep -E 'template|auc_drop_max' ae.yaml
```

Expected: `template: autoencoder` and `auc_drop_max: 0.05`, because only `autoencoder` answers an
`anomaly` output.

```bash
caravan init bad.yaml --no-input --dataset ../tests/fixtures/datasets/anomaly \
  --output-type anomaly --template mlp; echo "exit $?"
```

Expected: exit 2, naming `autoencoder` as the template that answers an `anomaly` output; no
`bad.yaml` exists.

## 6. Image data is recognised, not mishandled (spec edge case)

```bash
caravan init img.yaml --no-input --dataset ../tests/fixtures/datasets/images; echo "exit $?"
```

Expected: exit 1, the `image` column named as image file names, and a pointer to the manifest
reference for `image` inputs. No file written.

## 7. Abort leaves nothing (FR-004)

Start `caravan init x.yaml`, answer the first question, press Ctrl-C. Expected: no `x.yaml`, no
temporary file in the directory, no traceback.

## 8. Every offered combination validates (SC-002, SC-006)

```bash
pytest tests/contract/test_init_contract.py tests/integration/test_init_combinations.py -q
```

The combination test walks every registered template's starter against every fixture dataset and
every output type `init` offers for it, plus a third-party template registered in the test, and
asserts that each written file passes `load_manifest`.

## 9. The core still imports no framework (Principle XII)

```bash
pytest tests/layering -q
```
