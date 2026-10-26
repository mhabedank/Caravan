# Contract: The Documentation Site

What the site contains, how it is checked and when it is published. Pages and their sources are
listed in data-model.md §6.

## Navigation

The landing page (`docs/index.md`) carries the one `{toctree}`, in this order:

1. **Start:** Try it (`try-it.md`), Your own project (`guides/own-project.md`), On the board:
   LoRa32 (`guides/lora32.md`)
2. **Reference:** CLI (`reference/cli.md`), Manifest (`reference/manifest.md`), Rules
   (`reference/rules.md`), Budgets (`budgets.md`), Manifest changes (`manifest-changes.md`)
3. **Project:** Compatibility (`compatibility.md`), Roadmap (`roadmap.md`), Releases
   (`releases/0.1.0.md`), Board runs (`board-runs/index.md`, which lists the records)

The landing page also links the five main sections directly in its body, so each is one click away
(SC-005).

## The landing page

- what Caravan is, in three sentences;
- what it deliberately is not (Principle II);
- the install lines;
- the pipeline as one line: manifest → data → build (fit check) → train → quantize (gate) →
  export;
- the version it describes.

## CLI reference: one section per verb

```markdown
## caravan export

<purpose, one paragraph>

**Arguments.** `<manifest>` — …

**Options.**
- `--runs-dir <path>` — … (default `runs`)
- `--json` — …
- `-q`, `--quiet` — …

**Reads.** …   **Writes.** …   **Exit codes.** 0 …, 1 …, 2 …, 3 …, 4 …
```

## Manifest reference: one entry per field path

| Path | Type | Default | Allowed | Read by | Rules |
|---|---|---|---|---|---|
| `export.test_windows` | integer | `0` | 0–64; >0 needs `c_array` | export | — |

- Grouped by section: `model`, `input_features[]`, `output_features[]`, `preprocessing`,
  `dataset`, `trainer`, `random_seed`, `export`, the boards and their budgets.
- Per-type keys under `input_features[].preprocessing` and `output_features[]` say which type they
  belong to.
- One complete example manifest at the end, the example's own.

## Rules page: one heading per identifier

```markdown
### CF-14

**Checks:** … **Reported at:** <path> **Fix:** …
```

A retired identifier is `### CF-10 (retired)`, with the version that retired it and what replaced
it.

## Checks

| Check | Where | Fails when |
|---|---|---|
| `sphinx-build -W` | docs workflow; locally `uv run --group docs sphinx-build -W -b html docs _site` | a broken link or anchor, a page outside the toctree and not `orphan` |
| `tests/contract/test_docs_reference.py` | the default test job | a verb, option, field path, rule identifier, template, board or feature type is missing from its page |
| `try-it.md` step blocks | release `verify` job (existing) | the guide as written fails against the release |
| `guides/lora32.md` step blocks + `pio run` | firmware workflow | the firmware does not build for either LoRa32 environment |

## Publishing

| Trigger | Checks out | Version shown |
|---|---|---|
| release workflow, after `release` | the new tag | the tag's version |
| `workflow_dispatch` | input `tag`, default the latest release tag | that tag's version |

Never on a push. Never from a branch (FR-019, FR-021).
