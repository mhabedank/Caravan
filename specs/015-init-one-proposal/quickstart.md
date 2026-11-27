# Quickstart: validating feature 015

Runnable checks that the feature works end to end. The behaviour is specified in
[contracts/cli-init.md](./contracts/cli-init.md), [contracts/init-result.md](./contracts/init-result.md)
and [contracts/agents-md.md](./contracts/agents-md.md); this page only says how to see it.

## Prerequisites

- The repository with feature 015 built, the default installation: `uv sync` (no extras).
- A scratch directory beside the repository, with the synthetic data in reach:

```bash
mkdir -p /tmp/init-015 && cd /tmp/init-015
DATA=$OLDPWD/tests/fixtures/datasets/synthetic
```

## 1. One proposal, four answers (US1, SC-001, SC-008)

In a real terminal:

```bash
uv run --project $OLDPWD caravan init
```

Answer the data with `$DATA` (or pick it if offered), choose `s32k144` at the boards, press Enter at
the columns step, press Enter at the decision.

Expected: the proposal appears once before the boards, every line with a certainty word; the columns
step shows only `can_id` and `dlc`; the second proposal has a memory line for `s32k144` with
"lower bounds, estimated before building"; four answers in all; `wrote synthetic-mlp.yaml — valid`.
For SC-008, hand the same task to someone who has not used Caravan, without the docs: under 2 minutes.

```bash
uv run --project $OLDPWD caravan validate synthetic-mlp.yaml --no-report   # exit 0
```

## 2. Adjust one item (US1, scenario 6)

Run `caravan init --dataset $DATA --board s32k144 --overwrite`, answer `a` at the decision, pick the
window: the window table and strip appear as in feature 013. Choose 8, back at the proposal the
window line says `8 rows  answered`.

## 3. No person, no `--yes`: nothing written (US2, FR-012, FR-014, SC-004)

```bash
rm -f synthetic-mlp.yaml
time uv run --project $OLDPWD caravan init --dataset $DATA </dev/null; echo "exit $?"
ls synthetic-mlp.yaml 2>&1
```

Expected: the proposal on standard error, `no board: … for example --board esp32 (registered: …)`,
the accepting command; `exit 2`; well under 5 seconds; no file.

## 4. `--yes` (US2, FR-013, FR-016)

```bash
uv run --project $OLDPWD caravan init --dataset $DATA --board s32k144 --yes </dev/null; echo "exit $?"
```

Expected: `took 2 uncertain proposals: can_id as category (…), dlc as category (…)`, the file written,
`exit 0`, the path on standard output. Run it again: `exit 2`, naming `--overwrite`. Run it once more
without `--board`: `exit 2`, naming `--board` with an example.

## 5. The JSON preview and its round trip (US3, SC-006)

```bash
rm -f synthetic-mlp.yaml
uv run --project $OLDPWD caravan init --dataset $DATA --json > preview.json; echo "exit $?"
python3 -c 'import json; d=json.load(open("preview.json")); print(d["outcome"]); print(d["next"])'
eval "$(python3 -c 'import json; print(json.load(open("preview.json"))["next"].replace("caravan", "uv run --project $OLDPWD caravan", 1))')" > result.json
python3 -c 'import json; d=json.load(open("result.json")); print(d["outcome"], d["written"])'
```

Expected: `exit 2`, `proposed`, a `next` that adds `--board esp32 --yes --json`; the second run prints
`written ['synthetic-mlp.yaml']`. Standard output of both runs is exactly one JSON document.

## 6. `AGENTS.md` (US4)

```bash
rm -f synthetic-mlp.yaml AGENTS.md
uv run --project $OLDPWD caravan init --dataset $DATA --board s32k144 --yes --agents-md
head -3 AGENTS.md
echo "# mine" > AGENTS.md
uv run --project $OLDPWD caravan init --dataset $DATA --board s32k144 --yes --agents-md --overwrite
cat AGENTS.md
```

Expected: the guide of contracts/agents-md.md naming `synthetic-mlp.yaml`; on the second run
`kept AGENTS.md: it exists, and init never changes it`, the manifest rewritten, `AGENTS.md` still
`# mine`.

## 7. One interface (US5, SC-010)

```bash
uv run --project $OLDPWD caravan init --plain; echo "exit $?"     # 2, unknown option
uv run --project $OLDPWD caravan init --tui; echo "exit $?"       # 2, unknown option
cd $OLDPWD && grep -rIil --exclude-dir={specs,.venv,.git,.claude,.specify} \
  -e "authoring extra" -e "\[authoring" -e "authoring =" -e textual -e full-screen .
```

Expected: both exit 2; the search finds only `docs/releases/0.1.0.md` (the change note). The
constitution's history and the specs of feature 013 keep their record and are not searched; "an
authoring aid", the constitution's name for `init`, is not a match.

## 8. The suite

```bash
cd $OLDPWD
uv run pytest tests/contract tests/unit tests/integration tests/layering -q
uv run ruff check . && uv run ruff format --check .
```

Expected: green in the default installation, on every Python of the matrix; there is no `tests/tui`
any more and no `authoring` job in CI.
