# Phase 0 research: Documentation organised like Django's

Decided on 2026-10-29. R1–R4 rest on a spike — a small Sphinx project built with the exact pinned
versions, Sphinx 9.2.0 and myst-parser 5.1.0 — not on documentation of other versions.

## R1 — Linkable objects are built in

**Decision**: register four object kinds with `app.add_object_type()` in a new
`docs/_ext/caravan_objects.py`: `manifest-field` (role `mf`), `cli` (role `cmd`), `rule` (role
`rule`), `board` (role `board`).

**Proven**: in MyST, ```` ```{manifest-field} export.targets ```` declares the entry and
`` {mf}`export.targets` `` in running text resolves to `ref.html#manifest-field-export.targets`;
`` {cmd}`caravan export` `` resolves to `#cli-caravan-export`. Each declaration also lands in the
generated index as "export.targets (manifest field)", which is FR-013's index for free.

**Alternatives considered**: a full Sphinx domain class gives qualified-name lookups this site does
not need; a third-party package adds a dependency for fifteen lines (Principle XII); hand-written
labels with `{ref}` work but give no index and no per-kind role.

## R2 — An unknown name fails the build

**Decision**: set `nitpicky = True` in `docs/conf.py`. With `-W`, already used by every build, an
unresolved name is an error.

**Proven**: `` {mf}`export.nope` `` gives `WARNING: 'mf' reference target not found: export.nope`
and fails a `-W` build; `` {term}`nope` `` gives `WARNING: term not in glossary` and fails it too.
The current site, built with `nitpicky = True`, raises **no** new warning — turning it on costs
nothing today.

This is FR-014 with no new test, which is what FR-027 asks for.

## R3 — The glossary is built in

**Decision**: a ```` ```{glossary} ```` block in `docs/glossary.md`, linked with `` {term}`gate` ``.

**Proven**: resolves to `glossary.html#term-gate`. Seed the terms from the abbreviation table the
existing check already keeps (`tests/contract/test_docs_glossary.py`, `EXPANSIONS`), then the
concepts every tutorial part names: manifest, feature, template, window, quantization, int8, gate,
fit check, budget, stage, run, target, board, representative samples, vocabulary, normalization,
interface contract, provenance label, run report, C array.

## R4 — The boxes are built in; one is ours

**Decision**: notes, warnings and "see also" use the built-in admonitions
(`:::{note}`, `:::{warning}`, `:::{seealso}`; `colon_fence` is already enabled). The "you will
learn" box is the generic `:::{admonition} You will learn` with `:class: learn`. The theme styles
all four in the identity, in both colour schemes.

**Proven**: `:::{seealso}` renders as a classed box with no extension.

## R5 — Forwards that keep their anchor

**Decision**: extend `docs/_ext/redirects.py`. A forward may carry an anchor map; its stub runs a
short script first — `location.replace(map[hash] or target + hash)` — and keeps the meta refresh as
the fallback for a browser without scripts. Every forward appends the anchor by default, so a page
that moves whole (`compatibility`, the tutorial parts) keeps its anchors with no map at all.

**Why a map is needed at all**: three pages change their anchors, not only their address. The
manifest page is split, and its headings become objects whose ids differ:

| Old page | Old anchors (build of 011) | Example |
|---|---|---|
| `reference/manifest` | 54 | `#apiversion` → the `apiVersion` entry on `ref/manifest/top-level` |
| `reference/cli` | 12 | `#caravan-export` → `ref/cli#cli-caravan-export` |
| `reference/rules` | 62 | `#v-1` → `ref/rules#rule-V-1` |

The old anchors are a fact recorded from the build of feature 011, not a guess. The new side of
the map is read from the new build, never written by hand, because the exact form of an object's
id (its case, its separators) is Sphinx's to decide. The map is committed as data. A map entry that points at an anchor the new build does not have fails the
build, as a forward to a missing page already does.

**Alternatives considered**: keeping the old headings above the new objects would keep the anchors
but print every name twice; an HTTP redirect is not available on GitHub Pages.

## R6 — Previous/next inside one sequence

**Decision**: the theme renders previous/next from Sphinx's own `prev`/`next`, but only when the
neighbour is in the same sequence — the same folder (`intro/`, `topics/`, `howto/`).

**Proven**: Sphinx supplies `prev` and `next` from the table of contents (the spike's pages carry
`rel="prev"`/`rel="next"`). It chains across sections — the spike's page A had the glossary as its
previous page — so the bound is the theme's job. `intro/` reads as one sequence on purpose: at a
glance → installation → the tutorial → its four parts is the order a newcomer reads.

## R7 — Addresses

**Decision**: Django's tree (owner, Q2): `intro/` for first steps and the tutorial (`tutorial`,
`tutorial01`–`tutorial04`, as Django names its parts), `topics/`, `ref/`, `howto/`. Project pages
(`roadmap`, `releases/`, `credits`) keep their addresses; `credits.md` is written by
`scripts/imagery/place.py` at a fixed path. The full map: [contracts/addresses.md](./contracts/addresses.md).

## R8 — The manifest split

**Decision**: `ref/manifest/index.md` keeps "A first manifest" and "A complete example" and links one
sub-page per top-level section: `top-level`, `model`, `input-features`, `output-features`,
`preprocessing`, `defaults`, `trainer`, `export`. Each `###` field heading becomes a
`manifest-field` object with its dotted name.

`tests/contract/test_docs_reference.py` today reads one file and its headings. It is adapted to read
the sub-pages and the object declarations; what it checks — every field the parser knows has an
entry — does not change.

## R9 — Who names the pages by path

Recorded so the moves can land in one step with their callers:

| Caller | Names |
|---|---|
| `tests/train/test_route_legs.py` | parts 1, 2, 4 (renamed `test_tutorial.py`) |
| `tests/contract/test_docs_guide.py`, `tests/integration/test_readme.py` | part 1 |
| `tests/contract/test_docs_reference.py` | `reference/{cli,manifest,rules}.md` |
| `tests/contract/test_docs_glossary.py` | `concepts/*.md`, `route/*.md` |
| `.github/workflows/release.yml` | part 1 (runs it against the published release) |
| `.github/workflows/firmware.yml` | part 3 |
| `tests/contract/test_docs_hygiene.py` | the forward map's shape in `conf.py`; a stub's size |
| `tests/unit/test_release_note.py`, `docs/releases/0.1.0.md` | `manifest-changes.md` (the note links it) |
| `README.md` | the published URL of part 1 (line 48), `docs/budgets.md`, `docs/reference/{cli,manifest}.md` |
| `src/caravan/manifest/version.py` | `CHANGE_NOTE = "docs/manifest-changes.md"`, printed in an error; asserted by `tests/contract/test_cli_contract.py` |
| `src/caravan/env.py`, `src/caravan/manifest/schema/removed.py` | `docs/budgets.md`, `docs/manifest-changes.md` in comments and docstrings |
| `tests/unit/test_env_messages.py`, `pyproject.toml`, `CONTRIBUTING.md`, `.github/workflows/ci.yml` | `docs/budgets.md` in a comment or message |
| `examples/picket-mlp.yaml` | `docs/route/2-your-columns.md`, `docs/route/3-onto-a-board.md`, and the metaphor in the comments |

Corrected at analysis: the first version of this table said `src/` names nothing. It does —
`CHANGE_NOTE` is shown to a user whose manifest declares a retired version, so moving the page
without it would send them to a file that no longer exists.

## R10 — The header

**Decision**: `nav_pages` holds one entry, `("contents", "Documentation")`; the layout's existing
search link stays. The footer's "What is verified today" link follows the page to
`ref/compatibility`.

## R11 — The tutorial's opening box

**Decision**: each tutorial part opens with one box, not two. Today's leg box ("10 minutes", "you
end with…") and FR-018's "you will learn" become a single `learn` box: the minutes, three to five
points it teaches, and what you end with. Two boxes in a row at the top of a page is the clutter
the boxes exist to prevent.

## R12 — Linking policy in practice

**Decision**: the first use per `##` section links; headings and code never do; an object role is
preferred to a plain link whenever the name is an object. Details in
[contracts/writing.md](./contracts/writing.md). This is enforced by review, not by a test: a check
that counted links per section would be the test suite the owner declined.

## Baseline at implementation

Measured on 2026-10-29, on the tree before anything moved, on the owner's laptop:

- the `-W` build: 2.2 s wall time, 0 warnings;
- the site's weight as `docs-checks.yml` sums it (apparent bytes, `.doctrees` excluded):
  **1,287,614 B** against the 3,000,000 B ceiling. The tasks quoted 1,236,008 B from an earlier
  build; this is the figure the end of the feature is compared with;
- old anchors recorded in `contracts/old-anchors.json`: 54 (manifest), 12 (CLI), 62 (rules).
