# Contract: addresses

Every page's address names its type, as Django's do (FR-021, owner Q2). Addresses are shown without
the `.html` suffix.

## The new tree

| Address | Type | Layer | Was |
|---|---|---|---|
| `index` | landing | — | `index` (unchanged; ends after the tutorial cards, FR-025) |
| `contents` | overview | — | NEW — "Documentation" in the header |
| `glossary` | reference | — | NEW |
| `genindex` | reference | — | generated; "Index" on the overview (FR-013) |
| `intro/overview` | tutorial (from scratch) | — | NEW — Caravan at a glance, + the landing's "What it actually does" and "What Caravan is for" |
| `intro/install` | tutorial (from scratch) | — | NEW — + the landing's "What you bring" |
| `intro/tutorial` | tutorial | — | `route/index` |
| `intro/tutorial01` | tutorial | — | `route/1-first-model` |
| `intro/tutorial02` | tutorial | — | `route/2-your-columns` |
| `intro/tutorial03` | tutorial | — | `route/3-onto-a-board` |
| `intro/tutorial04` | tutorial | — | `route/4-when-it-does-not-fit` |
| `topics/pipeline` | topic guide | pipeline & CLI | NEW |
| `topics/templates` | topic guide | manifest | `concepts/templates` |
| `topics/feature-types` | topic guide | manifest | `concepts/feature-types` |
| `topics/budgets-and-gates` | topic guide | verification | `concepts/budgets-and-gates` |
| `topics/what-a-run-leaves` | topic guide | exported model & firmware | `concepts/what-a-run-leaves` |
| `ref/manifest/index` | reference | manifest | `reference/manifest` (split) |
| `ref/manifest/{top-level,model,input-features,output-features,preprocessing,defaults,trainer,export}` | reference | manifest | NEW — one per top-level section |
| `ref/cli` | reference | pipeline & CLI | `reference/cli` |
| `ref/rules` | reference | verification | `reference/rules` |
| `ref/boards` | reference | boards & targets | NEW — one entry per board |
| `ref/budgets` | reference | project | `budgets` — Caravan's own dependency, install and Python budgets, so it is listed with the project, not under verification (changed at implementation) |
| `ref/manifest-changes` | reference | manifest | `manifest-changes` |
| `ref/compatibility` | reference | boards & targets | `compatibility` |
| `ref/board-runs/index` | reference | exported model & firmware | `board-runs/index` |
| `howto/add-a-board` | how-to guide | boards & targets | NEW |
| `howto/choose-a-budget` | how-to guide | verification | NEW |
| `roadmap`, `releases/0.1.0`, `credits` | project | project | unchanged |

## Forwards

Every forward carries the reader's anchor across (see [forwards.md](./forwards.md)).

| Old address | New address | Anchor map |
|---|---|---|
| `route/index` | `intro/tutorial` | — |
| `route/1-first-model` | `intro/tutorial01` | — |
| `route/2-your-columns` | `intro/tutorial02` | — |
| `route/3-onto-a-board` | `intro/tutorial03` | — |
| `route/4-when-it-does-not-fit` | `intro/tutorial04` | — |
| `concepts/templates` | `topics/templates` | — |
| `concepts/feature-types` | `topics/feature-types` | — |
| `concepts/budgets-and-gates` | `topics/budgets-and-gates` | — |
| `concepts/what-a-run-leaves` | `topics/what-a-run-leaves` | — |
| `reference/manifest` | `ref/manifest/index` | **yes — 54 anchors** |
| `reference/cli` | `ref/cli` | **yes — 12 anchors** |
| `reference/rules` | `ref/rules` | **yes — 62 anchors** |
| `budgets` | `ref/budgets` | — |
| `manifest-changes` | `ref/manifest-changes` | — |
| `compatibility` | `ref/compatibility` | — |
| `board-runs/index` | `ref/board-runs/index` | — |
| `try-it` (existing) | `intro/tutorial` | — (was `route/index`: retargeted, no chain) |
| `guides/own-project` (existing) | `intro/tutorial02` | — (retargeted) |
| `guides/lora32` (existing) | `intro/tutorial03` | — (retargeted) |

A forward points at the final page, never at another forward.

## Who must follow

`tests/train/test_route_legs.py` (renamed `test_tutorial.py`), `tests/contract/test_docs_guide.py`,
`tests/contract/test_docs_reference.py`, `tests/contract/test_docs_glossary.py`,
`tests/integration/test_readme.py`, `.github/workflows/release.yml`, `.github/workflows/firmware.yml`,
`README.md`, the theme's footer link to what is verified today. All move in the same commit as the
pages (plan, step 2).
