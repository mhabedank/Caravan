# Quickstart: Validating Feature 001

Date: 2026-10-22 · Spec: [spec.md](./spec.md) · Contracts: [contracts/](./contracts/)

How to confirm that this feature works, end to end, on a machine with nothing installed. Each
scenario names the requirement it proves, so a reviewer can walk the list rather than take the
implementation's word for it.

## Prerequisites

- A supported Python: 3.14 or 3.15 (research R4).
- `uv` for environments, matching the sibling project's setup.
- No machine-learning framework. That is a precondition, not a missing step — scenario 6 depends
  on its absence.
- No network access is needed after the install, and no hardware at any point.

## Setup

```bash
uv venv --python 3.15
uv pip install -e ".[dev]"
```

For the budget scenarios, build and install the real distribution rather than an editable
checkout:

```bash
uv build
uv venv /tmp/caravan-clean --python 3.15
VIRTUAL_ENV=/tmp/caravan-clean uv pip install --no-cache dist/caravan_ml-*.whl
```

---

## Scenario 1 — The pilot manifest validates (US1, SC-004)

```bash
caravan validate tests/fixtures/manifests/valid/picket-mlp.yaml
```

Expected: a one-line confirmation on standard error, exit code 0, and a run directory under
`runs/` containing `report.json` with `"outcome": "valid"` and the dataset reference listed under
`unresolved`.

The unresolved entry is the point: a valid manifest does not mean a resolved dataset, and the
report says so without being asked.

## Scenario 2 — Every broken manifest is rejected for its own reason (US1, SC-002)

```bash
for f in tests/fixtures/manifests/invalid/*.yaml; do
  caravan validate "$f" --json
done
```

Expected: exit code 1 for every file, and for each one a JSON document whose `findings[0].rule`
is the rule identifier encoded in the file name — `cf-1-split-sum.yaml` fires `CF-1`,
`b-1-unknown-board.yaml` fires `B-1`, and so on. The fixture set has one file per rule in the data
model, and the test suite fails if a rule has no fixture.

Spot-check the message quality by eye on two of them:

```bash
caravan validate tests/fixtures/manifests/invalid/t-1-unknown-template.yaml
caravan validate tests/fixtures/manifests/invalid/unknown-field-misplaced.yaml
```

Expected: the first lists the registered template identifiers; the second says both where the
field was found and where it belongs. Neither mentions a Python type or a module path.

## Scenario 3 — The resolved manifest shows everything (US2, SC-007)

```bash
caravan render tests/fixtures/manifests/valid/pilot-min.yaml --stdout
```

Expected: a complete manifest on standard output — `train`, `verify` and `bench` present with
their defaults, `split` filled in as 0.7/0.15/0.15, `model.params.dropout` filled in from the
template's default, `formats` filled in. No field of the schema missing, nothing left implicit.

Run it twice and compare (SC-005):

```bash
caravan render tests/fixtures/manifests/valid/pilot-min.yaml --stdout > /tmp/a.yaml
caravan render tests/fixtures/manifests/valid/pilot-min.yaml --stdout > /tmp/b.yaml
cmp /tmp/a.yaml /tmp/b.yaml && echo "byte-identical"
```

Expected: `byte-identical`.

## Scenario 4 — The author's file is never touched (US2, FR-006)

```bash
sha256sum tests/fixtures/manifests/valid/picket-mlp.yaml > /tmp/before
caravan validate tests/fixtures/manifests/valid/picket-mlp.yaml
caravan render  tests/fixtures/manifests/valid/picket-mlp.yaml
sha256sum -c /tmp/before
```

Expected: `OK`. This is the scenario that matters for an archived manifest: reading it, including
migrating it, must not rewrite it.

## Scenario 5 — An older manifest still loads (US3, SC-006)

The schema has only one version today, so this is exercised through the test that registers a
synthetic older version (research R6):

```bash
pytest tests/unit/test_migration.py -v
```

Expected: a manifest declaring the synthetic older version loads with its transform applied; the
file on disk is unchanged; the report names both the declared and the effective version; and a
manifest declaring an unknown version is refused with exit code 1 and a message listing
`caravan/v0`.

Check the refusal by hand too:

```bash
caravan validate tests/fixtures/manifests/invalid/v-1-unknown-version.yaml
```

Expected: exit code 1, and a message naming `caravan/v0` as what this build implements. Not a
crash, and not a silent reinterpretation.

## Scenario 6 — Nothing drags in a training framework (US4, FR-026)

```bash
pytest tests/layering -v
```

Expected: three checks pass — no framework in the loaded module table after importing the core; the
end-to-end runs still pass while importing a framework is made to raise; and the built
distribution declares no framework among its dependencies.

Confirm by hand that the clean environment really has none:

```bash
VIRTUAL_ENV=/tmp/caravan-clean uv pip list | grep -Ei 'tensorflow|torch|jax' || echo "none present"
VIRTUAL_ENV=/tmp/caravan-clean caravan validate tests/fixtures/manifests/valid/picket-mlp.yaml
```

Expected: `none present`, then exit code 0. The tool does its job on a machine that could not train
a model if it wanted to.

## Scenario 7 — The install stays within budget (US4, SC-003)

```bash
VIRTUAL_ENV=/tmp/caravan-clean-2 uv pip install --no-cache --dry-run dist/caravan_ml-*.whl
```

Expected: two runtime dependencies resolved, `pydantic` and `ruamel.yaml`, plus their own
transitive requirements, and a total download well inside 50 MB — around 4 MB with the chosen set.
The measured form of this check runs in continuous integration and fails the job over 30 seconds or
50 MB; the budget's headroom is deliberate, reserved for the analysis feature rather than available
for convenience.

## Scenario 8 — The lists the errors promise actually exist (FR-022, FR-023)

```bash
caravan templates
caravan boards
```

Expected: `mlp` with its one-line summary; `esp32`, `s32k144`, `stm32h743`. The board list is what
the unknown-board message cites, so the two must agree — a test asserts that they come from the
same registry.

## Scenario 9 — No command reaches the network (contract guarantee)

```bash
pytest tests/contract/test_no_network.py -v
```

Expected: pass. Socket creation is made to raise for the duration, and every command still behaves
as specified. Principle VIII in executable form, and the precondition for Principle VI's promise
that publication cannot happen before compliance is checked.

---

## What a reviewer should conclude

If scenarios 1 through 9 pass on a clean machine, then: a manifest can be authored and checked
without a training framework, every rejection is actionable and pinned by a fixture, the effective
configuration of a run is written down and comparable, an archived manifest cannot become
unreadable, and the two budgets the constitution sets for the package itself are measured rather
than asserted.

What is deliberately **not** demonstrated here, because it is not in this feature: training,
quantization, export, footprint analysis, emulated verification, hardware benchmarks and
publication. No scenario above produces a number about hardware, so no provenance label appears
anywhere in this feature's output (Principle IV holds by absence).
