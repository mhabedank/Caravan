# Implementation Plan: Documentation organised like Django's

**Branch**: `012-docs-restructure` | **Date**: 2026-10-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-docs-restructure/spec.md`

## Summary

Give Caravan's documentation Django's shape: one overview page behind a header that carries only
"Documentation" and "Search"; every page typed and addressed by its type (`intro/`, `topics/`,
`ref/`, `howto/`); the route-and-legs metaphor replaced by a tutorial in four parts; the manifest
reference split into one page per section; every manifest field, CLI command, validation rule and
board an object that running text links by name; a glossary; and the boxes and previous/next links
that make Django's pages scannable.

Everything it needs is already in the site's pinned build tools. A spike on the pinned Sphinx 9.2
and myst-parser 5.1 (research R1–R4) showed that linkable object types, the glossary, the boxes and
the previous/next data all exist there, and that an unknown name fails the build. The two pieces the
tools do not give — forwards that keep an anchor, and previous/next that stays inside one sequence
— are about forty lines of the project's own code.

## Technical Context

**Language/Version**: Markdown (MyST) for pages; Jinja for the theme; Python 3.13 for the two small
Sphinx extensions in `docs/_ext/`.

**Primary Dependencies**: Sphinx 9.2.0 and myst-parser 5.1.0, pinned in the `docs` dependency group.
Unchanged. No dependency is added anywhere (FR-026).

**Storage**: files.

**Testing**: the site build with every warning an error, now with `nitpicky = True` so an unknown
name fails it (FR-014). The existing documentation checks, adapted to the new paths. No new test
file (FR-027).

**Target Platform**: the static site on GitHub Pages, built by `docs.yml` per release.

**Project Type**: a documentation site.

**Performance Goals**: the documentation job stays inside ten minutes (FR-028); today it runs in about
3 seconds of checks plus setup.

**Constraints**: every moved address forwards, anchors included (FR-010, FR-021); the tutorial's
commands still run in CI from their new paths; nothing added to the distribution.

**Scale/Scope**: 20 pages today, about 35 after; 106 reference objects (43 manifest fields, 8 CLI
commands, 52 rules, 3 boards); at least 20 glossary terms; 19 forwarded addresses (16 new, 3 existing
retargeted), three of them with anchor maps (54 + 12 + 62 old anchors).

## Constitution Check

*GATE: verified before Phase 0 and again after Phase 1.*

| Principle | Verdict | How this feature complies |
|---|---|---|
| IV. Measured, Emulated or Estimated | PASS | Moving and rewriting pages keeps every provenance label on a number about hardware (FR-023). The no-hedging rule removes softening, never a label. |
| XII. Small Core, Few Dependencies | PASS | No dependency, extra or group is added. The two gaps the build tools leave — anchor-keeping forwards and sequence-bounded previous/next — are closed with about forty lines in `docs/_ext/` and the theme, under the rule that code the project can own in a few hundred readable lines must not become a dependency. Third-party options (`sphinx-reredirects`, `sphinx-design`, a full domain package) were rejected on exactly that ground. |
| Resources & Cost Discipline | PASS | One documentation job, one Python, no extras, inside ten minutes. The added strictness (`nitpicky`) costs nothing measurable: the current site builds with it and raises no new warning (R2). |
| Development Workflow & Quality Gates | PASS | The spec lists the principles it touches; this table checks them before and after design. |
| The owner's D5 decision (feature 010) | Respected | The site gets checks, not a test suite. Unresolved names fail the build; existing checks follow the pages; no test file is added. |

**Post-design re-check (after Phase 1)**: unchanged. The design adds two short extension modules,
theme CSS and templates, and pages. It adds no dependency, no CI job and no test file.

## Project Structure

### Documentation (this feature)

```text
specs/012-docs-restructure/
├── plan.md              # This file
├── research.md          # Phase 0: what the spike proved, and the decisions
├── data-model.md        # Phase 1: pages, objects, terms, forwards, boxes
├── quickstart.md        # Phase 1: how to verify each story
├── contracts/
│   ├── addresses.md     # the new tree and every old -> new address
│   ├── objects.md       # the four object kinds: directive, role, anchor, index entry
│   ├── forwards.md      # how a forward keeps its anchor
│   └── writing.md       # the no-hedging rule, the linking policy, the boxes
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
docs/
├── index.md                    # landing: metaphor out, ends after the tutorial cards (FR-024, FR-025)
├── contents.md                 # NEW  the documentation overview — "Documentation" in the header
├── glossary.md                 # NEW
├── intro/                      # first steps
│   ├── overview.md             # NEW  Caravan at a glance (+ landing's "What it does", "What it is for")
│   ├── install.md              # NEW  Installation (+ landing's "What you bring")
│   ├── tutorial.md             # <- route/index.md
│   └── tutorial01..04.md       # <- route/1-first-model.md … route/4-when-it-does-not-fit.md
├── topics/                     # <- concepts/*, + NEW pipeline.md
├── ref/
│   ├── manifest/index.md       # <- reference/manifest.md: a first manifest, the complete example
│   ├── manifest/{top-level,model,input-features,output-features,preprocessing,defaults,trainer,export}.md
│   ├── cli.md  rules.md        # <- reference/
│   ├── boards.md               # NEW  one entry per board
│   ├── budgets.md  manifest-changes.md  compatibility.md   # <- top level
│   └── board-runs/index.md     # <- board-runs/index.md
├── howto/                      # NEW  add-a-board.md, choose-a-budget.md
├── roadmap.md  releases/  credits.md   # project pages, unchanged addresses
├── conf.py                     # nav_pages -> Documentation; nitpicky; forwards + anchor maps
├── _ext/
│   ├── caravan_objects.py      # NEW  the four object kinds (~15 lines)
│   └── redirects.py            # forwards keep their anchor (~25 lines added)
└── _themes/caravan/
    ├── layout.html             # header; previous/next bounded to a sequence
    └── static/site.css         # boxes, object entries, previous/next

tests/contract/test_docs_{reference,guide,glossary}.py   # follow the pages
tests/integration/test_readme.py                          # follows part 1
tests/train/test_route_legs.py -> test_tutorial.py       # follows parts 1, 2, 4
.github/workflows/{release,firmware}.yml                 # name parts 1 and 3 by their new paths
README.md                                                 # links part 1 at its new address
scripts/imagery/place.py                                  # credits page unchanged; van record's placement renamed
```

**Structure Decision**: Django's own tree, `intro/ topics/ ref/ howto/`, as the owner chose (Q2).
Project pages and `credits.md` keep their addresses: they are not documentation types, and
`credits.md` is written by `place.py` at a fixed path. The address of every moved page is in
[contracts/addresses.md](./contracts/addresses.md).

## Implementation order

Smallest useful first, and nothing visible breaks between steps:

1. **Foundation**: the object kinds, `nitpicky`, the anchor-keeping forwards, the boxes and the
   bounded previous/next. Proven on the current pages before anything moves.
2. **Moves**: `git mv` every page to its address, the forwards and anchor maps, and every test,
   workflow and README path in the same step — so CI never runs a path that is gone.
3. **Reference objects**: the manifest split and its 43 fields, then the 8 commands, the 52 rules,
   the new boards page. The reference check is adapted to read objects instead of headings.
4. **The overview and the header**: `contents.md`; the header becomes Documentation · Search.
5. **The glossary and the linking pass** over tutorial, topic and how-to pages.
6. **New pages**: at a glance, installation (taking the landing's lower sections), the pipeline
   topic, the two how-to guides.
7. **The metaphor and the language**: the landing page, the tutorial's titles and boxes, the
   no-hedging pass.

## Complexity Tracking

No constitution violation to justify. One risk is tracked instead of hidden: the tutorial's files
are executed by a test, the release workflow and the firmware workflow, and step 2 moves them.
Moving the pages and their callers in one commit, and running the docs checks and the leg test
before it lands, is what keeps a release from running a path that no longer exists.
