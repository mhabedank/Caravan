# Quickstart: Validating Feature 009

How to show that the feature works, scenario by scenario. Commands run from the repository root
unless they say otherwise. Expected outcomes refer to the spec's acceptance scenarios and success
criteria.

## Prerequisites

- Python 3.13 with `uv`. The repository's usual environment: `uv sync --extra train --extra verify`.
- For the firmware: network access to the PlatformIO registry and `components.espressif.com`, and
  about 2 GB of disk for the first PlatformIO setup.
- For the board scenarios: a LILYGO LoRa32 and a USB cable. Only the owner runs these.

## 1. The site builds and is complete (Story 2, SC-003, SC-004, SC-005)

```bash
uv run --group docs sphinx-build -W -b html docs _site
uv run pytest tests/contract/test_docs_reference.py -q
```

Expected:
- **The build** exits 0. `_site/index.html` links the CLI reference, the manifest reference, the
  compatibility page, the roadmap and the board guide.
- **The test** passes.

Then remove one option from `docs/reference/cli.md` and run the test again. It must fail, naming
the verb and the option. Restore the option.

Then add an unlinked page under `docs/`. The build must fail with `toc.not_included`. Remove the
page.

## 2. Test windows come out of the export (FR-003, FR-004)

```bash
uv run caravan export examples/picket-mlp.yaml
run=$(ls -td runs/*/ | head -1)
ls "$run"model/test_windows.h
uv run python -c "import json,sys; print(json.load(open(sys.argv[1]))['test_windows'])" "$run"export.json
```

Expected:
- The header exists, and the record says 16 windows were written.
- The record also gives the selection rule, the per-class counts and the score step.
- Every class of the example appears.
- Run the export again: it is reused from the cache.
- Change `export.test_windows` to 8 and run again: only the export runs again.

## 3. The firmware builds for both LoRa32 environments (FR-009, SC-006)

The guide's own blocks, as the firmware workflow runs them:

```bash
python -m tests.support_docs docs/guides/lora32.md board-tools > /tmp/tools.sh
python -m tests.support_docs docs/guides/lora32.md board-copy > /tmp/copy.sh
python -m tests.support_docs docs/guides/lora32.md board-build > /tmp/build.sh
bash -euo pipefail -c '. /tmp/tools.sh; . /tmp/copy.sh; . /tmp/build.sh'
(cd examples/lora32 && pio run -e lora32-v1)
```

Expected:
- Both environments link.
- `pio run` prints the flash and RAM use.
- No warning comes from the generated headers.

## 4. On the board (Story 1, SC-001, SC-002), owner only

Follow `docs/guides/lora32.md` from an empty directory, through the `board-flash` block.

Expected:
- The OLED shows one screen per window and then the summary (contracts/board-output.md).
- The serial monitor shows the same lines and the run record block.
- `agreed 16/16`.
- `max_score_diff_steps` ≤ 1.
- The arena is labeled measured.

Commit the record block as `docs/board-runs/<date>-lora32.md`. Then update the `esp32` row of
`docs/compatibility.md` to `measured` (SC-008).

## 5. An own project (Story 4, SC-007), owner only

With a small CSV that is not the fixture, follow `docs/guides/own-project.md` to a manifest that
validates and exports for `esp32` with `test_windows` set. Then follow the board guide with that
run's `model/` files.

Expected: the only changes from the example are the ones the guide names. Any Caravan defect found
is fixed or listed under "Known limits" on the compatibility page.

## 6. Publishing (FR-019, FR-021)

After the owner has set Pages to "GitHub Actions" (research R2), dispatch `docs.yml` by hand with
the latest release tag.

Expected:
- `https://mhabedank.github.io/Caravan/` shows that version on every page.
- A push that touches only `docs/` starts no workflow.
