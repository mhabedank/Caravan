---
description: "Task list for feature 010: a website that teaches Caravan in half an hour"
---

# Tasks: A website that teaches Caravan in half an hour

**Input**: Design documents from `/specs/010-website-overhaul/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: The spec requires checks as deliverables, not as a TDD practice — FR-018, FR-020,
FR-034, FR-042, FR-045 and SC-012 each name a check that must exist and fail on a breach. They are
therefore implementation tasks inside the story whose claim they defend, not a separate test phase.

**Organization**: by user story, so each ships on its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel — different files, no dependency on unfinished work
- **[Story]**: US1 to US6, from spec.md

## Path Conventions

Single project. The site is `docs/`, its theme `docs/_themes/caravan/`, the firmware
`examples/esp32/`, the checks `tests/`. No file under `src/caravan/` changes except one comment
(T066).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: the directories and the one dependency this feature adds

- [X] T001 Create the site's new directories: `docs/route/`, `docs/concepts/`, `docs/_themes/caravan/static/`, `docs/_ext/`, and `tests/site/` with an `__init__.py`
- [X] T002 Add a pinned `site-checks` dependency group to `pyproject.toml` for the browser driver, with a comment stating what the plan's dependency gate established: it is never installed with the package, belongs to no extra, and leaves the distribution's dependency count unchanged
- [X] T003 [P] Vendor the two typefaces into `docs/_themes/caravan/static/fonts/` from the zoo's `src/mobility_model_zoo/site/static/fonts/`, together with their `OFL.txt` notice, which FR-028 requires to travel with the copy
- [X] T004 [P] Vendor the accessibility auditing library into `tests/site/vendor/` with its licence header and a comment that it is never deployed, mirroring the zoo's `site/checks_vendor/`
- [X] T005 [P] Add `docs/_themes/`, `docs/_ext/` and `tests/site/vendor/` to the lint and format exclusions in `pyproject.toml` where the copied files would otherwise be reformatted

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the identity and the build machinery every page needs. No page can be written in the
new design until this phase is done.

**⚠️ CRITICAL**: blocks every user story.

- [X] T006 Copy the zoo's `tokens.css` verbatim into `docs/_themes/caravan/static/tokens.css`, keeping its comments, and add a header recording the origin and the date, and that the two identities may drift with nothing keeping them in step (FR-028, contracts/design-tokens.md)
- [X] T007 Create `docs/_themes/caravan/theme.conf` inheriting `basic`, declaring `site.css` as the stylesheet
- [X] T008 Create `docs/_themes/caravan/layout.html` from the zoo's `base.html.j2`: the skip link, `.hd`/`.wrap.hd-in`/`.brand`, `main#main`, the footer, and the navigation built from the table of contents instead of the zoo's hard-coded links. The stylesheet loop MUST be `{% for css in css_files %}` with `pathto(css.filename, 1)` — the older `pathto(css, 1)` fails on the pinned Sphinx with a theme error naming neither template nor line (research R1)
- [X] T009 Port the zoo's `site.css` into `docs/_themes/caravan/static/site.css`, mapping its element and utility selectors onto the markup Sphinx emits for body content, and keeping `.prose`, `.wrap`, `.lead`, `.muted`, `.cap` as the layer the pages use
- [X] T010 [P] Draw Caravan's own mark into `docs/_themes/caravan/static/img/mark.svg` and a favicon beside it — its own, not the zoo's, as D4 requires
- [X] T011 Render the Caravan version on every page from `docs/_themes/caravan/layout.html`, reading it from `docs/conf.py`'s `release`. The previous theme supplied this through `html_title`, which T011 removes, so without this the version silently disappears from the site (FR-047)
- [X] T012 Point `docs/conf.py` at the theme: `html_theme_path = ["_themes"]`, `html_theme = "caravan"`, and remove the previous theme's options
- [X] T013 Create `docs/_ext/redirects.py`: a build hook that writes one forwarding stub per entry of a redirect map, each carrying a meta refresh, a canonical link and `noindex`, with `indexable` being "`false` for every forward, so a stub never competes with the page it points at" (data-model.md, Address)
- [X] T014 Register the redirect extension and an empty redirect map in `docs/conf.py`, to be filled by the stories that move pages
- [X] T015 Teach `docs/_themes/caravan/layout.html` and `docs/conf.py` a second layout chosen from the page's own front matter, so the landing page can declare it and every other page keeps the article layout (research R8)
- [X] T016 Write the design language to `docs/design/2026-10-27-design-language.md` — unpublished, as `exclude_patterns` already excludes `docs/design/` — covering the type scale, the palette with its contrast figures, the treatment of code, tables and figures, the vocabulary of the journey, the voice, what the accent is reserved for, and the statement that legibility wins over the identity wherever they conflict (FR-031, FR-032)

**Checkpoint**: the site builds in the new identity, pages can be written, and addresses can move.

---

## Phase 3: User Story 1 - The three-second verdict (Priority: P1) 🎯 MVP

**Goal**: a first screen that says what Caravan produces, from what, for whom, at what cost, and
offers exactly one way in.

**Independent Test**: show the first screen to five people who do not know the project for five
seconds, take it away, and ask what it does, what it refuses, and what the next step is. Needs no
other page finished.

- [X] T017 [US1] Create `docs/_themes/caravan/landing.html`: no sidebar, the verdict and the primary next step both above the fold at phone width, built on the layout from T014
- [X] T018 [US1] Rewrite `docs/index.md` as the landing page: what Caravan takes in, what it produces, and which hardware that output runs on, stated before any scrolling and without requiring the pipeline's internal stage names (FR-001, FR-005)
- [X] T019 [US1] State the cost of entry in `docs/index.md` — the reader's own tabular data and a supported Python version — and make the install's download weight discoverable before any install command appears (FR-002)
- [X] T020 [US1] Give `docs/index.md` exactly one primary next step, labelled with the time it takes, pointing at the route's first leg (FR-003)
- [X] T021 [US1] Move Caravan's scope in `docs/index.md` to after the benefit and rephrase it as scope rather than as a list of refusals (FR-004)
- [X] T022 [US1] State on `docs/index.md` which operating systems and Python versions the route is written for, so a reader on an unsupported one learns it before installing anything (FR-002, spec.md edge case "A reader on Windows")
- [X] T023 [US1] Add `tests/contract/test_docs_landing.py`: the landing page carries exactly one primary call to action, that call names a duration, the install weight is stated, and the scope section appears after the benefit section in document order (FR-002, FR-003, FR-004)
- [X] T024 [US1] Add the new pages to the toctree in `docs/index.md` so no page is left outside the navigation, and confirm `uv run sphinx-build -W -b html docs _site` is clean

**Checkpoint**: the landing page stands on its own and can be put in front of readers.

---

## Phase 4: User Story 2 - A model of my own inside fifteen minutes (Priority: P1)

**Goal**: legs 1 and 2 — the example run end to end, then the reader's own columns — reaching an
int8 model by the fifteen-minute mark.

**Independent Test**: a clean machine, the install done, a timer started at leg 1; an int8 model
file exists inside fifteen minutes, and a second one reads the reader's own columns. No hardware.

- [X] T025 [US2] Create `docs/route/index.md`: what the route is, the four legs, and what each one ends with, so a reader can see the whole half hour before starting
- [X] T026 [US2] Write `docs/route/1-first-model.md` — the example installed and run to an int8 model and its C array. Must carry every field the Leg entity requires: `duration` and `promise` before the first instruction, a named `outcome`, the `verification` by which the reader confirms it, the `next` leg and what it adds, and the `exit` for a reader who stops (FR-009, FR-010, FR-011, FR-013)
- [X] T027 [US2] Write `docs/route/2-your-columns.md` — the reader's own CSV and column types, re-running to a model of their own with their own accuracy figure, with the same Leg fields (FR-009 to FR-013)
- [X] T028 [US2] State in `docs/route/2-your-columns.md` which earlier results the reader's changes invalidate and the single command that re-establishes them (FR-015)
- [X] T029 [US2] Answer leg 1's two dead ends in place in `docs/route/1-first-model.md`, both **before** the install command rather than after it fails: a Python version the training extra does not support, and an operating system the route is not written for (FR-016, User Story 2 scenario 6, spec.md edge case "A reader on Windows")
- [X] T030 [US2] Answer leg 2's dead ends in place in `docs/route/2-your-columns.md`: a quantization gate that fails on the reader's data, pointing at leg 4; and the data shapes the pipeline refuses — wrong column types, one class, a file too small, no header row — with how each is recognised (FR-016)
- [X] T031 [US2] Explain each artifact in the leg that first produces it, replacing `try-it.md`'s closing list of thirty-two output files (FR-014)
- [X] T032 [US2] Mark the command blocks of `docs/route/1-first-model.md` and `docs/route/2-your-columns.md` with the `# step:` names the existing block extractor reads, so the commands are executable by a check rather than only readable
- [X] T033 [US2] Rename `tests/train/test_try_it_guide.py` to `tests/train/test_route_legs.py` and point it at the two new leg pages: every run command succeeds, the files each leg promises exist, and the export step's console still fits on one screen
- [X] T034 [US2] Extend `tests/contract/test_docs_guide.py` to check the legs' install and fetch commands name this version, replacing its reference to `docs/try-it.md`
- [X] T035 [US2] Add `tests/contract/test_docs_legs.py`: every leg page states a duration and a promise before its first command block, and ends with a verification step — the Leg invariant that "a leg whose outcome cannot be verified by the reader is not a leg" (data-model.md)
- [X] T036 [US2] Delete `docs/try-it.md` and add its address to the redirect map, forwarding to `docs/route/` (contracts/page-inventory.md)

**Checkpoint**: a reader reaches their own int8 model from the site alone, and the fifteen-minute
promise can be timed.

---

## Phase 5: User Story 3 - On hardware inside thirty minutes (Priority: P2)

**Goal**: leg 3 and the firmware behind it — a generic ESP32 answering test windows, checked
against the host, within thirty minutes of the start.

**Independent Test**: continue the timed run on a generic ESP32 development board and record when
the board first answers and whether its answers agreed. The no-hardware path is tested by following
the same leg without a board.

- [X] T037 [P] [US3] Create `examples/esp32/platformio.ini` targeting `esp32dev`, with `sdkconfig.defaults`, `CMakeLists.txt`, `src/CMakeLists.txt` and `src/idf_component.yml` derived from `examples/lora32/`
- [X] T038 [US3] Write `examples/esp32/src/main.cc` from `examples/lora32/src/main.cc` (198 lines): keep the inference and the comparison of the board's answers with the host's, and replace every display call with serial output. Carry over no OLED, pin or radio code (research R2)
- [X] T039 [P] [US3] Create `examples/esp32/src/model/README.md` saying which four generated files the reader copies here — `model_data.h`, `model_data.cc`, `resolver.h`, `test_windows.h` — and that the directory is otherwise empty
- [X] T040 [US3] Write `docs/route/3-onto-a-board.md` with all Leg fields, naming the board it was written against and what a reader holding a different ESP32 board has to change (FR-041), with command blocks marked `# step:` so a check can execute them
- [X] T041 [US3] State in `docs/route/3-onto-a-board.md` what agreement to expect between the board and the host, and what a disagreement means (User Story 3 scenario 2)
- [X] T042 [US3] Give `docs/route/3-onto-a-board.md` a path for a reader with no hardware that still ends in something countable, and say plainly which claims that path cannot support (FR-016, User Story 3 scenario 3)
- [X] T043 [US3] Label every figure leg 3 reports about the board with "exactly one of `estimated`, `emulated`, `measured`" (data-model.md, Hardware claim). The linker's RAM and flash figures are `estimated` — a linker is not a board — and no timing figure appears, because no benchmark exists (Principle IV)
- [X] T044 [US3] Extend `.github/workflows/firmware.yml` with a job step that builds `examples/esp32/` for `esp32dev` and executes leg 3's `# step:` blocks as written, beside the steps that already do this for the owner's board — the check that closes FR-042
- [X] T045 [US3] Add the generic project's paths to `firmware.yml`'s `pull_request` path filter, and record its linker figures into the run summary labelled as not measured on a board, as the existing step does
- [X] T046 [US3] Confirm the release workflow's call to `firmware.yml` now gates on the generic build too, so a documented path that does not compile blocks the release (FR-042)
- [X] T047 [US3] Add `tests/contract/test_docs_hardware.py`: no figure about a board appears on any page without exactly one provenance label, and no page labels a timing figure `measured` (FR-006, SC-016)
- [ ] T048 [US3] Add `examples/esp32/.gitignore` and `dependencies.lock` so the toolchain cache key in `firmware.yml` works for the new project as it does for the old

**Checkpoint**: the documented hardware path exists, is verified before every release, and the
thirty-minute promise can be timed.

---

## Phase 6: User Story 4 - I understand what I am choosing (Priority: P2)

**Goal**: the abbreviations expanded, the templates explained, every setting given prose, the rules
stated in words, and the gate taught by failing it.

**Independent Test**: audit every abbreviation and every setting on the site; each has its
explanation. Then give three described datasets to five readers and see whether they pick the
template the site's guidance implies.

- [X] T049 [P] [US4] Write `docs/concepts/templates.md`: what `MLP` stands for and what a multilayer perceptron is in one sentence assuming no machine-learning background, the same for `conv1d`, what shape of data each suits, what each costs in memory and flash, and which to pick for a described dataset (FR-018, FR-019)
- [X] T050 [P] [US4] Write `docs/concepts/feature-types.md`: `number`, `category` and `binary`, what each does inside the model, what preprocessing each brings, and what the firmware passes for it
- [X] T051 [P] [US4] Write `docs/concepts/budgets-and-gates.md`: what the int8 gate measures, what the fit check measures, why each stops a run rather than warning, and how a reader chooses their own budgets (FR-023)
- [X] T052 [P] [US4] Write `docs/concepts/what-a-run-leaves.md`: the run directory's artifacts and what each is for, linked from the legs rather than listed at the end of one (FR-014, FR-024)
- [X] T053 [US4] Write `docs/route/4-when-it-does-not-fit.md`: tighten a budget until the gate refuses, read the per-layer table it emits, and choose a budget — with all Leg fields, and placed beyond the thirty-minute promise (FR-016, research R5)
- [X] T054 [US4] Rewrite `docs/reference/manifest.md` so every setting carries the four prose fields the Setting entity requires — what it does, why its default is the default, when to change it, and what goes wrong at its extremes — while keeping its facts scannable for lookup (FR-020, FR-021)
- [X] T055 [US4] Replace the rule-code clusters in `docs/reference/manifest.md` cells with links to rules stated in words, so that no lookup entry consists only of type, default and codes (FR-021, FR-022)
- [X] T056 [US4] Rewrite `docs/reference/rules.md` so each rule says in words what it rejects and what the reader should do instead, with the identifier demoted to an anchor (FR-022)
- [ ] T057 [US4] Add the missing prose to `docs/reference/cli.md` entries: what each command and option is for, not only that it exists (FR-020)
- [ ] T058 [US4] Link each `docs/concepts/*.md` page from `docs/route/*.md` at the moment the concept first matters, and from the `docs/reference/*.md` entries that need it, without restating the explanation in either place (FR-024)
- [X] T059 [US4] Name once in `docs/reference/manifest.md` and `docs/concepts/feature-types.md`, where the site uses a term borrowed from another project's vocabulary, that it is borrowed, and explain it in Caravan's own words (FR-025)
- [X] T060 [US4] Add `tests/contract/test_docs_glossary.py`: every abbreviation appearing on a page is expanded at its first use on that page, driven by a list of abbreviations the site may use (FR-018, SC-007)
- [X] T061 [US4] Extend `tests/contract/test_docs_reference.py` so that every setting the schema admits has all four prose fields, and a setting with facts alone fails — the Setting invariant from data-model.md (FR-020, SC-008)
- [X] T062 [US4] Add a check to `tests/contract/test_docs_glossary.py` that every concept is defined on exactly one page, so the Concept invariant holds and two pages cannot drift apart (FR-024)
- [ ] T063 [US4] Delete `docs/guides/own-project.md`, fold its material into leg 2 and `docs/concepts/feature-types.md`, and add its address to the redirect map forwarding to `docs/route/2-your-columns` (contracts/page-inventory.md)

**Checkpoint**: a reader can change the model knowingly instead of copying the example.

---

## Phase 7: User Story 5 - The public face is the project's, not one person's (Priority: P3)

**Goal**: the withdrawn board and the project's internal development artifacts off every page a
reader sees, with no claim left standing after its evidence is removed.

**Independent Test**: search the built site for the board's names and for spec directories, feature
numbers and planning files; both return nothing, and no page lost a claim it needed.

- [X] T064 [US5] Delete `docs/guides/lora32.md` and the now-empty `docs/guides/` directory, and add its address to the redirect map forwarding to `docs/route/3-onto-a-board` with `noindex` (FR-039, FR-045, research R6)
- [X] T065 [US5] Remove the board from the eight remaining pages that name it: `docs/compatibility.md` (3), `docs/roadmap.md` (2), `docs/index.md` (2), `docs/board-runs/index.md` (2), `docs/releases/0.1.0.md` (1), `docs/reference/manifest.md` (1), `docs/reference/cli.md` (1), `docs/manifest-changes.md` (1)
- [X] T066 [US5] Rewrite the comment at `src/caravan/manifest/schema/export.py:27` so the header-size bound is justified without naming the owner's board, and the comment in `examples/picket-mlp.yaml:49` so it points at leg 3 instead of the deleted guide
- [X] T067 [US5] Re-ground each claim that rested on that board onto the generic ESP32, or restate it as not yet verified — never leave the conclusion standing with its evidence deleted. `docs/compatibility.md` and `docs/board-runs/index.md` carry most of these (FR-040)
- [X] T068 [US5] Rewrite `docs/board-runs/index.md` so the record it describes and the run it awaits are about the hardware the site documents, keeping the provenance label on every figure a record would hold (FR-040, FR-044)
- [X] T069 [P] [US5] Remove the 18 internal-artifact references from `docs/roadmap.md`, replacing each citation with what the site itself can show, and keep the roadmap's meaning (FR-043, FR-044)
- [X] T070 [P] [US5] Remove the 9 internal-artifact references from `docs/manifest-changes.md`, including the `specs/...` paths cited as evidence for schema decisions (FR-043, FR-044)
- [X] T071 [P] [US5] Remove the 6 internal-artifact references from `docs/releases/0.1.0.md` (FR-043)
- [X] T072 [P] [US5] Remove the 6 internal-artifact references from `docs/budgets.md`, which cite features and research notes as the source of its measurements — the measurements stay, their citation becomes something a reader can see (FR-043, FR-044)
- [X] T073 [P] [US5] Remove the 5 internal-artifact references from `docs/reference/rules.md` (FR-043)
- [X] T074 [US5] Add `tests/contract/test_docs_hygiene.py`: no published page matches the withdrawn board's names, and none matches a spec directory, a feature number, or a plan, task or analysis file; and every built page states the Caravan version it describes. Searches over the built or source pages, failing with the page and the match (SC-010, SC-011, FR-047)
- [X] T075 [US5] Add a check to `tests/contract/test_docs_hygiene.py` that every address in contracts/page-inventory.md resolves to a page or to a forward that resolves, and that every forward is `noindex` and in no table of contents (FR-045, SC-013)

**Checkpoint**: the site is the project's own, and nothing a reader sees points inward.

---

## Phase 8: User Story 6 - One design, readable everywhere (Priority: P3)

**Goal**: every page in one identity, measured rather than asserted — contrast, phone width, zoom,
screen reader, and no second visual language anywhere.

**Independent Test**: audit each page against the design language and against the accessibility
level, on a phone and a desktop, in both colour schemes.

- [X] T076 [US6] Extend `docs/_themes/caravan/static/site.css` to every element the pages actually use that the landing page did not exercise: tables, code blocks, admonitions, figures, definition lists and the search page
- [ ] T077 [US6] Make every table readable at phone width in `docs/_themes/caravan/static/site.css`, and reduce the tables of `docs/reference/manifest.md` and `docs/reference/rules.md` to the columns a reader genuinely scans across, so that no dense multi-column table carries an explanation (FR-038)
- [ ] T078 [US6] Reserve the single warm accent for the budget and its verdict throughout `docs/` — enforced in `docs/_themes/caravan/static/site.css` — and use it nowhere else (FR-029, contracts/design-tokens.md, R4)
- [ ] T079 [US6] Remove any colour literal left outside `tokens.css`, including the parts that are dark in both schemes, so a later change of identity is an edit to tokens rather than to pages (contracts/design-tokens.md)
- [ ] T080 [US6] Give every page under `docs/` a text alternative for each image, ordered heading levels, and no information carried by colour alone (FR-036)
- [X] T081 [US6] Confirm every page under `docs/` is complete and legible with images unavailable, and fix what depends on one (FR-037)
- [X] T082 [US6] Write `tests/site/test_a11y.py`: drive the built site in a headless browser, inject the vendored auditing library, and assert no violation at the A or AA level on every page in both colour schemes (FR-034, SC-012)
- [X] T083 [US6] Add to `tests/site/test_a11y.py` a check that no page scrolls sideways at phone width or at 200% zoom, including its code blocks and tables (FR-035, SC-012)
- [X] T084 [US6] Add `tests/contract/test_docs_tokens.py`: both colour schemes define every token the other defines, no interface colour is declared outside the token set, and the typefaces' notice is present beside them (contracts/design-tokens.md)
- [X] T085 [US6] Confirm `docs/_themes/caravan/static/tokens.css` honours the reader's system preference for colour scheme, and that neither scheme is derived from the other (FR-033)
- [ ] T086 [US6] Read every page against `docs/design/2026-10-27-design-language.md` and fix what does not match, so that any two pages share one type scale, one palette, one treatment of code and one voice (User Story 6 scenario 1)

**Checkpoint**: the site reads as one project made it, and the accessibility claim is a measurement.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T087 Extend `.github/workflows/docs-checks.yml` with the browser audit: install the browser, cache it, and run `tests/site/test_a11y.py` beside the page checks already there (contracts/checks.md)
- [X] T088 Make `.github/workflows/docs-checks.yml` fail when the job exceeds the ten minutes the constitution bounds it to, measuring and printing its own duration as the install-budget job does for the cold install (FR-050)
- [X] T089 Add the new check modules to `docs-checks.yml`'s pytest invocation — `test_docs_landing.py`, `test_docs_legs.py`, `test_docs_glossary.py`, `test_docs_hygiene.py`, `test_docs_hardware.py`, `test_docs_tokens.py` — so a documentation change runs all of them
- [ ] T090 Align `README.md` with the new site: the same verdict in the same words as the landing page, the board gone, the internal artifacts gone, and its links pointing at the route rather than the deleted guide
- [ ] T091 [P] Add this feature's row to `docs/roadmap.md` in the roadmap's own terms, without a feature number (FR-043)
- [ ] T092 [P] Record in `docs/compatibility.md` what the generic ESP32 path verifies and how far — compiled, not run — keeping each entry's provenance label (Principle IV)
- [ ] T093 Run the whole of `specs/010-website-overhaul/quickstart.md` steps 1 to 5 and fix what fails, including the deliberate-break checks it asks for
- [ ] T094 Carry out quickstart.md step 6 — the three promises measured over people, **and** the template choice of SC-009: give five readers three described datasets and record whether four pick the template the site's guidance implies. Record each result with its date, sample size and machine in `docs/design/2026-10-27-promise-measurements.md`, including whether any reader needed a source outside the site to finish a leg (SC-001 to SC-004, SC-006, SC-009)
- [ ] T095 Run the local validation the constitution's gate requires before a pull request is opened — lint, format, and the whole suite in the environments of the matrix in `.github/workflows/ci.yml` — then open one pull request for the feature

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: needs Setup. **Blocks every user story** — no page can be written in
  the new identity before the theme renders and addresses can move.
- **US1 (Phase 3)**: needs Foundational. Nothing else.
- **US2 (Phase 4)**: needs Foundational. Independent of US1, though the landing page's single next
  step points at leg 1, so shipping US1 alone leaves one link to a page that does not exist yet —
  ship US1 first only if that link is temporarily pointed at the old entry page.
- **US3 (Phase 5)**: needs Foundational. Leg 3 continues leg 2 for a reader, but the firmware, the
  workflow and the page are testable without legs 1 and 2 existing.
- **US4 (Phase 6)**: needs Foundational. T058 links concepts from the legs, so it is cheapest after
  US2 and US3; the concept pages and the reference rewrite do not depend on them.
- **US5 (Phase 7)**: needs Foundational. T064's forward points at leg 3, so T064 wants US3's page
  to exist — otherwise the forward lands nowhere and T075 fails.
- **US6 (Phase 8)**: needs Foundational, and is cheapest last, because it reads every page that
  exists. Running it before US4's pages exist means running it twice.
- **Polish (Phase 9)**: needs every story that will ship.

### Within Each User Story

The page comes before the check that defends it, and the firmware before the workflow that builds
it. Otherwise tasks marked [P] are independent.

### Parallel Opportunities

- Setup: T003, T004, T005 together.
- Foundational: T010 alongside T006 to T009; T016 can be drafted alongside any of them.
- US3: T037 and T039 together, before T038.
- US4: the four concept pages T049 to T052 are four independent files.
- US5: the five scrubbing tasks T069 to T073 are five independent files — the largest parallel
  block in the feature.
- US6: T082 and T084 are different files; T076 to T081 touch overlapping pages and should not be
  split across workers.
- Polish: T091 and T092 together.

### Parallel Example: User Story 5

```text
# After T064 to T068, launch the five scrubbing tasks together:
T069  docs/roadmap.md            (18 references)
T070  docs/manifest-changes.md   (9)
T071  docs/releases/0.1.0.md     (6)
T072  docs/budgets.md            (6)
T073  docs/reference/rules.md    (5)
# Then T074 and T075, which check all five at once.
```

## Implementation Strategy

**MVP is US1 alone**: the landing page in the new identity, after Foundational. That is twenty-two
tasks and it answers the owner's first and most-repeated complaint — a site unsuitable for
marketing — while every other page still works as it does today.

**Then US2**, which turns the MVP's promise into something a reader can finish. US1 and US2
together are the two P1 stories and deliver both halves of the stated goal bar the hardware.

**Then US3**, which completes the half hour, and carries the one piece of work with a release gate
behind it.

**US4, US5 and US6 are the P2–P3 tail** and can ship in any order, with two ordering costs worth
knowing: US5's forward for the withdrawn guide wants US3's page to exist, and US6 reads every page,
so running it before US4's pages are written means doing it twice.

**One sequencing warning.** US6 contains the accessibility audit, and it is the task most likely to
send work back into pages already written. Writing the pages against the design language from the
start (T016 before any page) is what keeps that from becoming a second pass over everything.
