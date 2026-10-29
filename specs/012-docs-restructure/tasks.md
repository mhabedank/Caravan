# Tasks: Documentation organised like Django's

**Input**: Design documents from `/specs/012-docs-restructure/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: no test task appears below. FR-027 forbids a new test suite, and the owner's D5 decision
in feature 010 removed the last one. The check is the build: `-W` with `nitpicky = True` fails on an
unresolved name (research R2). The four existing documentation checks are *adapted*, never added to.

**Organization**: by user story, so each lands as a working increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — a different file, no unfinished dependency
- **[US#]**: the user story this task serves; setup, foundational and polish tasks carry none

## Path Conventions

Paths are from the repository root, `/Users/m.habedank/Projects/private/caravan`. Page addresses
without a suffix are as published; the file is `docs/<address>.md`.

---

## Phase 1: Setup

**Purpose**: record the two facts that the current tree holds and the new tree cannot — the old
anchors, and today's build cost.

- [X] T001 Build the current site and record every heading id of the three pages whose anchors
      change, into `specs/012-docs-restructure/contracts/old-anchors.json` as
      `{"reference/manifest": [...], "reference/cli": [...], "reference/rules": [...]}`:
      `uv run --group docs sphinx-build -W -b html docs _site`, then read the `id=` attributes of
      `_site/reference/{manifest,cli,rules}.html` — section and heading ids only (an `id` on a
      `<section>` or a heading), not the theme's own ids on the header and search form. Expect **54, 12 and 62** ids (research R5); if a
      count differs, record the real one and note it in the file. This is data, captured before the
      pages move — not a guess, and not recoverable afterwards.
- [X] T002 Record today's baseline in `specs/012-docs-restructure/research.md` under a new
      "Baseline at implementation" heading: the `-W` build's wall time, its warning count (0), and
      the site's byte size as the weight gate in `.github/workflows/docs-checks.yml` measures it
      (1,236,008 B against the 3,000,000 B ceiling). FR-028 and the weight gate are both judged
      against these numbers.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the machinery every story needs, then the moves. Proven on the current pages *before*
anything moves (plan, step 1), so a failure is attributable.

**⚠️ CRITICAL**: no user story work begins until T012's gate is green.

### The machinery

- [X] T003 Create `docs/_ext/caravan_objects.py` registering the four object kinds with
      `app.add_object_type()` per [contracts/objects.md](./contracts/objects.md): `manifest-field`
      (role `mf`), `cli` (role `cmd`), `rule` (role `rule`), `board` (role `board`). Each takes
      `indextemplate` so the generated index reads "export.targets (manifest field)" (FR-013).
      Add `"caravan_objects"` to `extensions` in `docs/conf.py`.
- [X] T004 Set `nitpicky = True` in `docs/conf.py` and prove it costs nothing today: the current
      pages must still build with `-W` and raise no new warning (research R2). This is FR-014's
      whole enforcement.
- [X] T005 Extend `docs/_ext/redirects.py` per [contracts/forwards.md](./contracts/forwards.md): a
      `caravan_redirects` value may be a string or `{"to": ..., "anchors": {...}}`; the stub runs
      `location.replace(map[hash] || target + hash)` with the meta refresh kept as the no-script
      fallback; every forward appends the reader's anchor by default; the build fails on a forward to
      a missing page, a forward that points at another forward, or an anchor-map entry whose target
      anchor the new build does not contain.
- [X] T006 [P] Style the four boxes in `docs/_themes/caravan/static/site.css`: `note`, `warning`,
      `seealso` and the custom `learn` class (`:::{admonition} You will learn` + `:class: learn`,
      research R4). All four distinct from each other and from running text, in both colour schemes
      (FR-017). Also style a reference object entry — its name, and the `**Type** … · **Default** …`
      first line.
- [X] T007 [P] Render previous/next in `docs/_themes/caravan/layout.html` from Sphinx's own
      `prev`/`next`, but only when the neighbour's address is in the same folder (`intro/`,
      `topics/`, `howto/`) — research R6: Sphinx chains across sections, so the bound is the theme's.
      Style the pair in `docs/_themes/caravan/static/site.css`.

### The moves (one step, with every caller — plan step 2)

- [X] T008 `git mv` every page to its new address exactly as
      [contracts/addresses.md](./contracts/addresses.md) lists: `route/*` → `intro/tutorial`,
      `intro/tutorial01`–`04`; `concepts/*` → `topics/*`; `reference/manifest` →
      `ref/manifest/index`; `reference/{cli,rules}` → `ref/{cli,rules}`; `budgets`,
      `manifest-changes`, `compatibility` → `ref/*`; `board-runs/index` → `ref/board-runs/index`.
      `roadmap`, `releases/`, `credits` keep their addresses.
- [X] T009 Register all 19 forwards in `docs/conf.py`'s `caravan_redirects` — the 16 new ones and
      the 3 existing retargeted (`try-it` → `intro/tutorial`, `guides/own-project` →
      `intro/tutorial02`, `guides/lora32` → `intro/tutorial03`), each pointing at the final page and
      never at another forward. Page-level only at this stage: anchors are appended by default, and
      the three anchor maps arrive with the pages whose anchors change (T021, T030, T031).
- [X] T010 Repoint every caller in the same commit as T008, per research R9: `git mv
      tests/train/test_route_legs.py tests/train/test_tutorial.py` and update its three leg paths
      and the names inside it; `tests/contract/test_docs_guide.py` and
      `tests/integration/test_readme.py` (part 1); `tests/contract/test_docs_reference.py`
      (`ref/{cli,rules}.md`, `ref/manifest/`); `tests/contract/test_docs_glossary.py` (`topics/*.md`,
      `intro/tutorial*.md`); `.github/workflows/release.yml:170` (part 1);
      `.github/workflows/firmware.yml:64` (part 3); `README.md:48` (part 1's published URL, updated
      not forwarded); and the footer's "what is verified today" link in
      `docs/_themes/caravan/layout.html` → `ref/compatibility`. Also, per research R9 as corrected
      at analysis: `src/caravan/manifest/version.py`'s `CHANGE_NOTE` and the assertion on it in
      `tests/contract/test_cli_contract.py`; the link in `docs/releases/0.1.0.md` (its text still
      names `manifest-changes.md`, which `tests/unit/test_release_note.py` reads); README's other
      paths (`docs/budgets.md`, `docs/reference/{cli,manifest}.md`); the comments and messages in
      `src/caravan/env.py`, `src/caravan/manifest/schema/removed.py`,
      `tests/unit/test_env_messages.py`, `pyproject.toml`, `CONTRIBUTING.md`,
      `.github/workflows/ci.yml`; and `examples/picket-mlp.yaml`'s two page paths. Adapt
      `tests/contract/test_docs_hygiene.py` to the forward map's new shape (a value may be a
      mapping) and measure a stub's content without its script, since an anchor map makes the
      stub longer without giving it anything a reader reads.
- [X] T011 Repair every table of contents for the new tree. `root_doc` stays `index` (the landing).
      Decided at analysis, so previous/next has one order to follow: `docs/index.md` carries one
      hidden `toctree` holding only `contents`, and `contents` (T015) owns the order of every other
      page; the landing's cards are plain links, not a second table of contents. Until T013 writes
      the overview, `contents.md` is a stub with that hidden `toctree`. Also a `toctree` on
      `docs/intro/tutorial.md` over its four parts, one on `docs/ref/manifest/index.md` (filled in
      T020), and no `caption` naming an old section. Every page must be reachable, or `-W` fails on
      an orphan.
- [X] T012 Run the gate before anything else starts: `uv run --group docs sphinx-build -W -b html
      docs _site` clean, then `uv run --group dev --group docs pytest -q tests/contract/
      tests/integration/test_readme.py tests/train/test_tutorial.py`. Open
      `_site/route/1-first-model.html` and `_site/reference/manifest.html#preprocessing` in a browser
      and confirm both land on the new page (FR-010, SC-005).

**Checkpoint**: every old address answers, every caller names a path that exists, the four object
kinds and the boxes exist. User stories can start.

---

## Phase 3: User Story 1 — Find the way in from one page (P1) 🎯 MVP

**Goal**: one overview page, reached from a header that carries only Documentation and Search, from
which every layer's reference is one click.

**Independent Test**: from the landing page open the overview; for each of the five layers reach its
reference in one further click (SC-001). The header shows exactly two items.

- [X] T013 [US1] Write `docs/contents.md` — the documentation overview — in this order
      (FR-002, FR-003): **First steps** with a "From scratch" row (Caravan at a glance,
      Installation) and the tutorial's four parts; **Getting help** — the glossary, the Index of
      reference objects, what is verified today (`ref/compatibility`), and the issue tracker as the
      place to report a problem; **How the documentation is
      organized**, naming the four types (tutorials, topic guides, reference guides, how-to guides);
      then one section per layer — the manifest; the pipeline and the CLI; boards and targets;
      verification; the exported model and the firmware — each with a one-line definition and
      grouped links; then the project (roadmap, releases, credits) and the Index.
- [X] T014 [US1] Point the header at it: `nav_pages = [("contents", "Documentation")]` in
      `docs/conf.py` (research R10), the existing search link kept in
      `docs/_themes/caravan/layout.html`. Nothing else in the header (FR-001).
- [X] T015 [US1] Give `docs/contents.md` a hidden `toctree` covering every page in the new tree, in
      reading order (intro, topics, ref, howto, glossary, project), so no page is an orphan and
      previous/next follows one order (T011).
- [X] T016 [US1] Repoint the landing page's three buttons in
      `docs/_themes/caravan/landing.html`: the tutorial's first part, `ref/cli` and
      `ref/manifest/index` — one click from the landing to either reference (SC-001).
- [X] T017 [US1] Verify: build with `-W`, then walk quickstart's "Story 1" — count the clicks to
      every layer's reference from any page (two) and to `ref/cli` and `ref/manifest/index` from the
      landing (one).

**Checkpoint**: the site has a front door. US1 is shippable alone.

---

## Phase 4: User Story 2 — Look up one manifest field fast (P1)

**Goal**: the manifest reference split into one page per top-level section, every field an entry
with its type and default, every deep link from the old single page still landing on its field.

**Independent Test**: for ten sampled fields, reach the entry from the overview in at most two
clicks (SC-002); `reference/manifest.html#preprocessing` lands on the preprocessing page.

- [X] T018 [US2] Split `docs/ref/manifest/index.md`: keep "A first manifest" and "A complete
      example" (both must still validate), and link one sub-page per top-level section.
- [X] T019 [US2] (T019–T021 land in one commit: between the split and the map, old deep links into
      the manifest page would reach the top of a page.) Create the eight sub-pages
      `docs/ref/manifest/{top-level,model,input-features,output-features,preprocessing,defaults,trainer,export}.md`
      by moving each section's text out of the old page — same words, new home.
- [X] T020 [US2] Turn all **43** field headings into `manifest-field` objects named by their dotted
      name (`export.targets`, `preprocessing.window_size`), per
      [contracts/objects.md](./contracts/objects.md): the first line of each entry is content, not
      directive options — `**Type** … · **Default** …`. Add the `toctree` on
      `docs/ref/manifest/index.md` over the eight pages.
- [X] T021 [US2] Build, read the new ids out of `_site/ref/manifest/*.html`, and write the
      `reference/manifest` anchor map into `docs/conf.py` — all 54 old anchors from T001's file,
      each to its new page and anchor. The new side is read from the build, never typed by hand
      (research R5). A missing target fails the build (T005).
- [X] T022 [US2] Adapt `tests/contract/test_docs_reference.py` to read the sub-pages and their
      `manifest-field` declarations instead of one page's headings. What it checks is unchanged:
      every field the parser knows has exactly one entry (SC-003, FR-011).
- [X] T023 [US2] Verify with quickstart's "Story 2": the ten-field click count, and the headless
      Chrome check that `reference/cli.html#caravan-export`-style deep links end at the entry —
      run it for `reference/manifest.html#preprocessing` and two field anchors.

**Checkpoint**: the longest page is gone and every old deep link into it still works.

---

## Phase 5: User Story 3 — Every name in the text is a link (P1)

**Goal**: commands, rules and boards become objects too; a glossary; and running text that links
every name it mentions, with an unresolved name failing the build.

**Independent Test**: on a tutorial or topic page every field, command, rule and board name is a
link, and the first "gate" in a section links to the glossary while the second does not (FR-012,
FR-016). `genindex` lists every object with its kind.

- [X] T024 [US3] Turn the **8** command sections of `docs/ref/cli.md` into `cli` objects named
      `caravan <command>`, keeping the "By task" table at the top as links to them.
- [X] T025 [P] [US3] Turn the **52** rule sections of `docs/ref/rules.md` into `rule` objects named
      by their code (`V-1`).
- [X] T026 [P] [US3] Write `docs/ref/boards.md` with one `board` object per board — **3** today —
      each naming what the code says about it, and link it from the overview's "boards and targets"
      layer.
- [X] T027 [US3] Write `docs/glossary.md` as one `{glossary}` block, alphabetical, **at least 20
      terms** of one or two sentences each (FR-015), seeded from `EXPANSIONS` in
      `tests/contract/test_docs_glossary.py` plus the concepts the tutorial names: manifest,
      feature, template, window, quantization, int8, gate, fit check, budget, stage, run, target,
      board, representative samples, vocabulary, normalization, interface contract, provenance
      label, run report, C array (research R3). Each term points to the topic guide that explains
      it, where one exists.
- [X] T028 [US3] Add the glossary to `docs/contents.md`'s "Getting help" and to the hidden `toctree`
      (the Index is already there from T013).
- [X] T029 [US3] The linking pass over `docs/intro/tutorial*.md`, `docs/topics/*.md` and
      `docs/howto/*.md` per [contracts/writing.md](./contracts/writing.md) and research R12: the
      first use per `##` section links, later uses do not; headings and code never link; an object
      role (`{mf}`, `{cmd}`, `{rule}`, `{board}`) is preferred to a plain link whenever the name is
      an object. Enforced by review — a link-counting check would be the test suite the owner
      declined.
- [X] T030 [US3] Write the `reference/cli` anchor map into `docs/conf.py`: 12 old anchors, new side
      read from `_site/ref/cli.html`.
- [X] T031 [P] [US3] Write the `reference/rules` anchor map into `docs/conf.py`: 62 old anchors, new
      side read from `_site/ref/rules.html`. Note the case: `#v-1` → `#rule-V-1`.
- [X] T032 [US3] Extend `tests/contract/test_docs_reference.py` to the other three kinds — every
      command, rule and board the code defines has exactly one entry (SC-003) — and repoint
      `tests/contract/test_docs_glossary.py` at `docs/glossary.md` for its abbreviations.
- [X] T033 [US3] Verify: `-W` build clean with `nitpicky`; then prove it refuses — add
      `` {mf}`export.nope` `` to a page, build, expect `'mf' reference target not found`, remove it.
      Open `genindex.html` and confirm each kind appears (FR-013).

**Checkpoint**: all three P1 stories are in. This is the feature's substance.

---

## Phase 6: User Story 4 — Learn the pieces from scratch (P2)

**Goal**: the "From scratch" row — an at-a-glance overview and an installation page — plus the
pipeline topic guide, with the landing page's lower sections moved into them.

**Independent Test**: a reader finishes `intro/overview` in under ten minutes and can name the stages
a manifest goes through; `intro/install` ends with one command that proves the install; part 1 links to it instead of
repeating it.

- [X] T034 [US4] Write `docs/intro/overview.md` — Caravan at a glance — carrying one manifest
      through every stage with a link per stage, saying what Caravan is for and what it leaves out.
      Move the landing page's "What it actually does" and "What Caravan is for" sections into it
      (FR-025).
- [X] T035 [US4] Write `docs/intro/install.md`: what a reader needs, how to install, and one
      command that proves it. Move the landing page's "What you bring" into it (FR-025).
- [X] T036 [US4] Cut the moved sections from `docs/index.md` so the landing ends after the tutorial
      cards (FR-025). The two new pages are linked from `docs/contents.md`'s "From scratch" row;
      the landing has no "First steps" section and gains none.
- [X] T037 [US4] Replace the install steps repeated at the top of `docs/intro/tutorial01.md` with a
      link to `intro/install`.
- [X] T038 [P] [US4] Write `docs/topics/pipeline.md` — the topic guide on the pipeline and the CLI:
      the stages, what each consumes and leaves, and where the manifest decides. Ends with a
      `seealso` to `ref/cli` (FR-020).
- [X] T039 [US4] Add all three pages to the `intro/`/`topics/` sequence and to `docs/contents.md`,
      and check the sequence reads at a glance → installation → the tutorial → its four parts
      (research R6).

**Checkpoint**: a newcomer has a path that starts before the tutorial.

---

## Phase 7: User Story 5 — Know what a page will teach, and where to go next (P2)

**Goal**: one "you will learn" box at the top of every tutorial part and topic guide, a "see also"
at the end of every topic guide, and previous/next that stays inside its own sequence.

**Independent Test**: part 4's "next" does not jump to a topic guide; the first topic guide's
"previous" is not a tutorial part; all four box kinds stay legible in both colour schemes.

- [X] T040 [US5] Replace the old leg box at the top of each of `docs/intro/tutorial01.md`–`04.md`
      with a single `learn` box — the minutes, three to five points it teaches, and what you end
      with (research R11: one box, not two).
- [X] T041 [P] [US5] Add a `learn` box of three to five points to each of `docs/topics/pipeline.md`,
      `templates.md`, `feature-types.md`, `budgets-and-gates.md`, `what-a-run-leaves.md` (FR-018).
- [X] T042 [P] [US5] End every page in `docs/topics/` with a `seealso` box pointing at its layer's
      reference (FR-020).
- [X] T043 [US5] Convert the notes and warnings already written as plain paragraphs across
      `docs/intro/`, `docs/topics/` and `docs/ref/` into `:::{note}` and `:::{warning}` — a warning
      only where something will fail or cost data ([data-model.md](./data-model.md), Box).
- [X] T044 [US5] Verify the sequence edges in the built site: part 4 has no "next", the first topic
      guide has no "previous", and no pair crosses `intro/` → `topics/` → `howto/` (FR-019). Toggle
      the colour scheme and check all four box kinds (FR-017).

---

## Phase 8: User Story 6 — Recipes for the two things readers ask most (P3)

**Goal**: the first two how-to guides, in the voice of a recipe.

**Independent Test**: following "Add a board" with a datasheet ends with the board listed by
`caravan boards` and accepted in `export.targets`; "Choose a budget" ends with an
`accuracy_drop_max` taken from a run's own figures.

- [X] T045 [US6] Write `docs/howto/add-a-board.md`: from a datasheet to a board the CLI lists and
      `caravan validate` accepts in `export.targets`. Links `ref/boards` and `ref/compatibility`.
      One step records the source of every value taken from the datasheet, as the constitution's
      gate before adding a board description requires of the project's own boards.
- [X] T046 [P] [US6] Write `docs/howto/choose-a-budget.md`: from a run's own figures to an
      `accuracy_drop_max`, keeping every provenance label on a hardware number (FR-023, Principle
      IV).
- [X] T047 [US6] Add `howto/` to `docs/contents.md` under its layers and to the hidden `toctree`,
      with its own previous/next sequence.

---

## Phase 9: Polish — the metaphor and the language

**Purpose**: FR-024, FR-022 and FR-025. Last, because it touches pages every story above rewrote.

- [X] T048 Remove the route-and-legs metaphor from `docs/_themes/caravan/static/site.css`: rename
      `.leg-1`–`.leg-4` to the tutorial's own class names, change the `content: "LEG 1"` corner
      figures to the part's number, and rename the comments that explain them. The tile images keep
      their directory ids under `docs/_static/images/` — those ids are recorded in each
      `image.yaml` provenance record and in `docs/credits.md`; renaming them would rewrite
      provenance for no reader's benefit.
- [X] T049 Remove it from `docs/index.md` and `docs/_themes/caravan/landing.html`: the tile
      headings, the band's own heading, and the button label "Start the route" → the tutorial. The
      same in `README.md` ("The route's first leg") and in the comments of `examples/*.yaml`
      (FR-024).
- [X] T050 Remove it from the tutorial's own pages — `docs/intro/tutorial.md` and
      `tutorial01.md`–`04.md`: titles, headings, box text, and every "leg" in running text. A
      renamed heading changes its anchor; an old deep link to it then reaches the top of its part.
      Accepted: the tutorial's headings were never a reference to link into, unlike the three pages
      with anchor maps.
- [X] T051 Rename the van image's placement in `scripts/imagery/place.py` and the affected
      `docs/_static/images/*/image.yaml` placement labels so no placement is named after a leg; then
      re-run `place.py` and confirm `docs/credits.md` is rewritten with the same records and the
      aggregate stays under `AGGREGATE_CAP`.
- [X] T052 The no-hedging pass over every page under `docs/` (FR-022): remove "about N minutes",
      "from the start of", "roughly", "should be fine", "half hour" and the rest of
      [contracts/writing.md](./contracts/writing.md)'s banned list. Keep every Principle IV
      provenance label — a label is not a hedge (FR-023).
- [X] T053 Prove both are gone with the two greps in [quickstart.md](./quickstart.md) under "The
      metaphor and the language" — the metaphor grep over `docs --include=*.md` excluding
      `_static/` and `releases/`, and over `README.md` and `examples/`, and the hedging grep. Expect nothing from either. Release notes
      record history and are excluded on purpose.
- [X] T054 Run the whole of [quickstart.md](./quickstart.md): the strict build, all six stories,
      the headless-Chrome anchor checks, `git diff --stat main -- pyproject.toml uv.lock` (nothing,
      FR-026), `git diff -M --diff-filter=A --name-only main -- tests | wc -l` (0, FR-027), and the
      contract and integration checks.
- [X] T055 Check the two budgets the constitution sets: the documentation job's duration under ten
      minutes (FR-028, SC-008) and the site's bytes under the 3,000,000 B ceiling in
      `.github/workflows/docs-checks.yml`, both against T002's baseline. About fifteen new pages are
      text; report the real figures.
- [X] T056 Run the local validation the constitution's gate requires before a pull request is
      opened — lint, format, and the whole suite in the environments of the matrix in
      `.github/workflows/ci.yml`. This feature touches `src/`, `tests/`, two workflows and
      `scripts/`, so it is not a documentation-only change, and the framework matrix will run on it.
- [X] T057 Close the feature: add a "Status at close" section to `specs/012-docs-restructure/tasks.md` recording what was built,
      the final anchor counts actually mapped, and anything left — as feature 011's tasks.md does.

---

## Dependencies

**Phases**: Setup (T001–T002) → Foundational (T003–T012) → US1 → US2 → US3 → US4 → US5 → US6 →
Polish (T048–T057; T056 is the gate before the pull request). The gate at T012 blocks every story.

**Inside the foundation**: T003 and T004 before any object is declared; T005 before T009; T008 and
T010 in the same commit (plan, Complexity Tracking — a release workflow must never name a path that
is gone); T011 after T008.

**Between stories**:

- US1 depends on the foundation only. It is the MVP and ships alone.
- US2 depends on T003 (the `manifest-field` kind) and T005 (the anchor map). It links from US1's
  overview, so US1 first reads better, but the two do not block each other.
- US3 depends on T003 and on US2 (the linking pass links fields, so the fields must be objects
  first).
- US4 depends on US1 (it fills the "From scratch" row) and moves sections out of the landing page.
- US5 depends on US4 for the pipeline guide's box; otherwise only on T006 and T007.
- US6 depends on US3 for `ref/boards` and on T006 for its boxes.
- Polish depends on everything: it rewrites pages US4, US5 and US6 touch.

**Anchor maps are deliberately split**: T021 with the manifest pages, T030 and T031 with the CLI and
rules objects. Each map can only be written once the new build has the anchors it points at.

## Parallel opportunities

- T006 and T007 — different files, both pure theme work.
- T025 and T026 run beside T024: three separate reference pages.
- T030 and T031 — two independent maps in `conf.py`; write them in one edit if the same hand does
  both.
- T041 and T042 across the five topic guides; T045 and T046 are two unrelated how-to pages.
- T034 and T038 — `intro/overview` and `topics/pipeline` do not touch each other.

## Implementation strategy

**MVP**: Setup + Foundational + US1 (T001–T017). At that point every old address answers, the header
is Documentation · Search, and one page leads to every layer. It is worth publishing on its own.

**Then, in priority order**: US2 removes the site's worst page. US3 is what the owner admires in
Django and the reason `nitpicky` is on. US4 and US5 make the pages read like Django's. US6 starts the
how-to section that will keep growing.

**Each phase ends buildable**: `uv run --group docs sphinx-build -W -b html docs _site` clean, plus
the contract checks. Nothing half-moved is ever committed — the moves and their callers are one
commit by design.

---

## Status at close (2026-10-29)

**Built.** All 57 tasks. The site is organised like Django's: a contents page behind a header of
"Documentation" and "Search"; `intro/` (Caravan at a glance, Installation, the tutorial in four
parts), `topics/` (five guides, the pipeline guide new), `ref/` (the manifest reference split into
an overview and eight section pages, CLI, rules, a new boards page, budgets, schema changes, what is
verified today, board runs), `howto/` (Add a board, Choose a budget), and a glossary of 30 terms.
The route-and-legs metaphor is gone from every page, the README, the examples, the theme and the
workflows.

**Reference objects: 114**, each with exactly one entry, all in the generated index by kind:
51 manifest fields, 8 commands, 52 rules, 3 boards. The plan said 43 fields; the eight
`defaults.<type>.*` fields are fields the parser knows and had no entry, so they got one (FR-009).
`nitpicky` with `-W` refuses an unknown name, proven with `export.nope`.

**Forwards: 19**, three with anchor maps. Mapped anchors: **54** (manifest), **12** (CLI),
**62** (rules), every one resolved against the new build by the build itself. Old deep links into the
tutorial and topic pages carry their anchor across unchanged; a tutorial heading that was renamed
lands at the top of its part (accepted, T050).

**Checks.** `-W` build clean. Docs checks adapted, none added: 0 new test files against this
branch's last commit (`test_route_legs.py` renamed to `test_tutorial.py`). Local validation as the CI
matrix runs it: ruff check and format clean; core suite 667 passed on 3.13, 3.14 and 3.15; verify
suite 640 passed on 3.13 and 3.14; whole suite with both extras 914 passed, 12 skipped; the tutorial
test runs parts 1, 2 and 4 from their new paths. `pyproject.toml` changes only two comments; no
dependency, extra or group added (FR-026).

**Budgets.** Site weight 1,524,314 B of the 3,000,000 B ceiling (baseline 1,287,614 B). Cold `-W`
build 5.2 s (baseline 2.2 s); the documentation job stays far inside ten minutes, which it already
enforces with a timeout and an elapsed-time check.

**Decided during implementation.**
- The install block moved to `intro/install.md`. `test_docs_guide.py`, `test_readme.py` and the
  release workflow read `install` there and `fetch`/`run` from part 1.
- `ref/budgets` holds Caravan's own dependency and install budgets, not a model's, so the contents
  page lists it with the project rather than under verification (contracts/addresses.md updated).
- The theme had never rendered Sphinx's own pages: search and the generated index were empty since
  feature 010. `layout.html` now has a `body` block, and loads scripts on the search page only.
  Without this neither the header's Search (FR-001) nor the Index (FR-013) would work.
- Boards got a "description file" reference on `ref/boards` so the how-to can link every field.
- The forwarding stub's no-script refresh sits inside `<noscript>`, so it cannot race the script that
  carries the anchor. The hygiene check measures a stub without its script.
- `scripts/imagery/series/siebdruck.yaml` still names legs in its `placement` notes. It holds the
  owner's uncommitted work and nothing reads that field; the placed records and the credits page
  were changed instead.
- The theme's `img/leg-4.svg` was renamed `img/part-4.svg`; the four `route-*` image ids stay
  (FR-024's exemption).

**Left.** SC-007 (five readers shown the contents page) is a test with people and is not run here.
The headless-browser checks confirm each old address lands on its new page; that the browser also
scrolls to the mapped anchor rests on the build's check that every mapped anchor exists.

