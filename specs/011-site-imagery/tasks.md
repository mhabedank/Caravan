---

description: "Task list for feature 011: imagery for the site"
---

# Tasks: Imagery for the site

**Input**: Design documents from `/specs/011-site-imagery/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: no test tasks. Feature 010's D5 removed the website's checks deliberately — "the site gets
checks, not a test suite" — and this feature adds exactly one check, the weight gate the owner chose
in clarification (FR-029). Verification otherwise happens through the placement command's own
refusals, the site build with every warning an error, and [quickstart.md](./quickstart.md).

**Organization**: by user story. Stories 1–3 already exist in draft on this branch, so their tasks
are mostly confirmation and small corrections; story 4 is new work and carries the weight of the
feature.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies)
- **[Story]**: US1–US4, mapping to the spec's user stories
- **(owner)**: must be run by the owner on the CUDA machine. This session cannot: the Spark is
  behind a VPN it cannot reach and its own container has no GPU (Assumptions).

## Path Conventions

Scripts live in `scripts/imagery/` and are outside the distribution. Placed records live in
`docs/_static/images/<id>/`. Nothing goes in `src/` or `tests/`.

---

## Phase 1: Setup

**Purpose**: stop generated artifacts leaking into the repository, and say where the new copy came from

- [X] T001 Add `scripts/imagery/.gitignore` ignoring `series/*.html` and `rounds/`, and delete the stray generated page `scripts/imagery/series/subjects.html` — it is output of `sheet.py subjects`, not source, and is currently untracked in the working tree
- [X] T002 [P] Extend the "Copied, not shared" note in `scripts/imagery/README.md` to cover the placement half now being copied from the zoo's features 016 and 019 (records, derivatives, the XMP marker, the credits page), with the date and the statement that the two may drift (FR-006)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the art direction is read by three of the four stories, so it is settled first

**⚠️ CRITICAL**: T003 blocks US1 (the page renders the aspect) and US2 (the aspect picks the render size)

- [X] T003 State `aspect` explicitly on all twenty subjects in `scripts/imagery/series/siebdruck.yaml` — only 6 carry it today and the other 14 rely on the `"3:2"` default in `sheet.py`/`gen.py`; FR-002 requires each subject to carry its aspect ratio, and the permitted values are `16:9` (rendered 1344×768) and `3:2` (rendered 1200×800)

**Checkpoint**: the series file is complete per FR-002 — every subject carries id, prompt, aspect, scene, alt and placement

---

## Phase 3: User Story 1 - Decide the subjects before spending the GPU (Priority: P1) 🎯 MVP

**Goal**: one page that lists every subject the series will render, so prompts get argued with while
arguing is free.

**Independent Test**: build the page from the series file alone, with no rendered image, and read it.
Every subject has a prompt, an intended placement and an alt text; no subject repeats another; the
style and negative sentences appear once, in full.

- [X] T004 [US1] Confirm `write_subjects` in `scripts/imagery/sheet.py` lists every subject grouped by theme with its prompt, aspect, intended placement and alt text, and states the style and negative sentences in full, now that T003 makes every aspect explicit (FR-021, FR-002) — and while reading it, confirm the subjects are Caravan's own rather than the zoo's and that the style sentence reserves the warm accent for the one object each picture is about (FR-003)
- [X] T005 [US1] Confirm the summary line and the per-entry reserve tag in `write_subjects` in `scripts/imagery/sheet.py` report the nineteen placed subjects and the one held in reserve (FR-004, research R10)

**Checkpoint**: the written form of the art direction stands on its own, with no GPU spent (SC-001)

---

## Phase 4: User Story 2 - Render a round (Priority: P1)

**Goal**: one command renders every subject at several seeds and writes the images beside a manifest
recording exactly how each was made.

**Independent Test**: a draft run at low step count produces one file per subject per seed plus a
manifest whose entries match the files; a second run over the same directory renders nothing.

- [X] T006 [P] [US2] Record in `scripts/imagery/series/siebdruck.yaml` (as a comment beside `models.draft`) and in `scripts/imagery/README.md` — which FR-001 requires to hold both models with their licences and model cards — that the draft model FLUX.2-klein-4B takes no negative prompt — `gen.py` passes one only for a model declaring `true_cfg_scale` — so the clichés FR-005 names are excluded on the final pass only, and a draft is read for comprehension, not for lettering (research R8)
- [X] T007 [US2] Confirm `gen.py --plan` prints 76 file names for nineteen subjects at four seeds, and 80 with `--reserve`, and touches no GPU (FR-017)
- [X] T008 [US2] **(owner)** Run the draft pass — `--model draft --seeds 2 --out /work/rounds/draft` — then rewrite the prompts of the subjects the model plainly does not understand and re-draft only those with `--only theme/subject` (FR-015, FR-016); while the container is up, confirm it runs with no account, token or credential present and reaches nothing but the model host (FR-011)
- [ ] T009 [US2] **(owner)** Run the final pass as one command over the whole series (FR-012) — `--model final --seeds 4 --out /work/rounds/1`, about four hours unattended — and confirm the manifest carries every FR-018 field for a spot-checked image: model id and loaded revision, licence, model card, the complete prompt and negative prompt as sent, seed, steps, guidance, width, height, series, date, hardware class, container digest, repository commit and the generator script's SHA-256
- [ ] T010 [US2] **(owner)** Confirm resumption and determinism of `scripts/imagery/gen.py` against the round directory: interrupt the run and restart the same command, which must render only what is missing and leave `manifest.json` entries untouched (FR-014, SC-002); re-render one subject at the same seed on the same machine and confirm the image is identical (SC-005)

- [ ] T011 [US2] **(owner)** Confirm the second-round path of `scripts/imagery/gen.py`: write the subjects picked `none` into `/work/rounds/1/next.txt`, one `theme/subject` per line, then run `--model final --seeds 4 --seed-base 1000 --out /work/rounds/2` and confirm it renders only those subjects and that no seed repeats round 1's. SC-003 expects up to five of the twenty subjects to need another round, so this is an expected path rather than an edge case (FR-013, FR-015, Edge Cases "A second round")

**Checkpoint**: a round exists on the owner's machine with provenance for every candidate

---

## Phase 5: User Story 3 - Pick from a contact sheet (Priority: P1)

**Goal**: one page showing every candidate grouped under its subject and numbered, from which the
owner picks or says "none of these", and downloads `picks.yaml`.

**Independent Test**: build the sheet from a rendered round and pick on it. Picks survive a reload;
the downloaded file names the chosen number for each subject and `none` for the rest.

- [X] T012 [US3] Confirm `write_round` in `scripts/imagery/sheet.py` puts every candidate under its subject, numbers them within the subject, shows the subject's prompt, and links each candidate to its full-size file at a thumbnail wide enough to spot stray lettering in (FR-022; `THUMB_WIDTH` is 520)
- [X] T013 [US3] Confirm the sheet keeps picks across a reload in browser storage and writes them out as `picks.yaml` naming exactly one candidate number or `none` per subject (FR-023), and that it sends nothing anywhere and opens without a server (FR-025)
- [X] T014 [P] [US3] Confirm `write_round` in `scripts/imagery/sheet.py` shows a subject with no rendered candidate as a subject with no candidate rather than omitting it (FR-024)
- [X] T015 [P] [US3] Confirm the `CSS` block in `scripts/imagery/sheet.py` keeps both pages legible in the light and the dark colour scheme using the site's own four inks (FR-026)
- [ ] T016 [US3] **(owner)** Decide the round at the sheet — one pick or a `none` for every subject — and download `picks.yaml` (SC-004); at least fifteen of the twenty subjects should have something worth placing (SC-003)

**Checkpoint**: a chosen set of images exists; the work that cannot be redone cheaply is done

---

## Phase 6: User Story 4 - Place a picked image on the site (Priority: P2)

**Goal**: a picked image is brought into the repository at the widths the pages use, with its
provenance and its disclosure, and appears on its page.

**Independent Test**: place one image, build the site, and check its page, its weight and its
provenance record.

### The placement command

- [X] T017 [US4] Create `scripts/imagery/place.py` with a PEP 723 header declaring `requires-python = ">=3.13"` and dependencies `pyyaml>=6` and `pillow>=11` only — it runs outside the container, so FR-009 requires the declaration to be inline, plus the argument surface of [contracts/cli.md](./contracts/cli.md): positional round directory, `--picks`, `--only`, `--focal` (default `0.5,0.5`), `--id`, `--dry-run`; nothing else may be imported (research R11 — the zoo's own path drags in opencv, onnxruntime and rapidocr)
- [X] T018 [US4] Implement the focal crop in `scripts/imagery/place.py`: take the largest box of the subject's aspect (`16:9` or `3:2`) centred on the focal point as fractions in 0–1, clamped to the edges, then resize with `Image.Resampling.LANCZOS` to height `round(width * img.height / img.width)`
- [X] T019 [US4] Implement the three-width WebP encode in `scripts/imagery/place.py` at 480, 960 and 1600 px (FR-027), each written with `save(..., "WEBP", quality=q, method=6, xmp=packet)` at descending quality 72, 68, 64, 60 until the result is inside its per-width cap of `{480: 60_000, 960: 140_000, 1600: 300_000}` bytes, failing with the width and the cap named if quality 60 still exceeds it
- [X] T020 [US4] Implement the XMP packet in `scripts/imagery/place.py` carrying `Iptc4xmpExt:DigitalSourceType` set to the literal `http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia` and `xmp:CreatorTool` naming the series and the model, so every derivative discloses its origin inside the file (FR-032, research R3)
- [X] T021 [US4] Enforce the aggregate cap in `scripts/imagery/place.py`: the three derivatives together must stay within 118,000 bytes, which is one image's share of the site ceiling, and the failure message must state the figure, the image's total and that the site budget is what it protects (research R2)
- [X] T022 [US4] Implement the record writer in `scripts/imagery/place.py` producing `docs/_static/images/<id>/image.yaml` against [contracts/image-record.schema.json](./contracts/image-record.schema.json): `id` matching `^[a-z0-9]+(-[a-z0-9]+)*$`, `series`, `theme`, `subject`, the whole `generation` recipe copied verbatim from the manifest entry, `licence` fixed to the constant `CC0-1.0`, a non-empty `placements` array, `scene`, `alt` ending in `(AI-generated image)`, `focal_point` as two numbers in 0–1, `aspect`, `source` (width, height, sha256 of the render, with the PNG itself not copied in) and `derivatives` keyed `480`/`960`/`1600` each with `file`, `bytes` and `sha256`, so the recipe survives placement and the image stays traceable to the run that made it (FR-020) — and no zoo triage field (`checks`, `measures`, `round`, `phash`, accent shares), per FR-007 and research R4
- [X] T023 [US4] Implement the refusals in `scripts/imagery/place.py`, each a non-zero exit with nothing written: the picked file has no entry in the round's `manifest.json` (`<file> is not in <manifest>` — this is FR-019, the rule the whole provenance chain rests on); the target record directory already exists (`<dir> exists; remove it first`); a derivative or the aggregate exceeds its cap; the subject carries no `alt` or no `scene` in the series file
- [X] T024 [US4] Implement the credits page in `scripts/imagery/place.py`: rewrite `docs/credits.md` from every record on disk in `id` order, each entry carrying the image, the scene as its heading, a disclosure sentence naming the model, its licence, the hardware class and the date, the model card link, the pages the image is used on, and the CC0-1.0 deed at `https://creativecommons.org/publicdomain/zero/1.0/`; the page must contain the words "AI-generated" (FR-033) and must be written here rather than generated by the site build, so FR-010 holds (research R5)

### Wiring the site

- [X] T025 [P] [US4] Add `html_static_path = ["_static"]` to `docs/conf.py` so Sphinx copies `docs/_static/images/` verbatim into the build, with no build step of this feature's own (FR-010, research R7)
- [X] T026 [P] [US4] Add the credits link to the single footer in `docs/_themes/caravan/layout.html` with link text containing "AI-generated", so it appears on every page (FR-034, research R6)
- [X] T027 [P] [US4] Record in `NOTICE` the licence of each model used and that the generated images themselves are CC0-1.0 (FR-030)

### Measure before committing to nineteen

- [X] T028 [US4] Place exactly one image — the first screen subject — with `place.py`, then measure the real weight of its three derivatives and compare with the 104 KB an image the zoo's 92 records average and the 118,000 byte aggregate cap (research R2). **If it comes in materially heavier, stop and raise it**: the remedies are dropping the 1600 px width off non-hero subjects or moving to AVIF, and both reopen a decision the owner has already made, so neither is applied silently
- [X] T029 [US4] Build `docs/` and confirm the one placed image serves at the right width, its `image.yaml` is published beside it under `_static/images/<id>/`, `docs/credits.md` names it with its model, licence, date and hardware class, and the footer from `docs/_themes/caravan/layout.html` links the credits on every page

### The rest of the images, and the pages

- [ ] T030 [US4] Place the remaining picked images with `place.py`, leaving a `none` subject unplaced and its page as it is
- [X] T031 [US4] Put each placed image on its page in `docs/`, served from the three derivatives with a `srcset` and a `sizes` attribute, `width` and `height` set to avoid layout shift, `loading="lazy"` and `decoding="async"` except on the first screen, and the record's alt text — and confirm every page stays complete and understandable with images unavailable (FR-027, FR-028)
- [ ] T032 [US4] Retire `hero.svg` and `leg-1.svg` … `leg-4.svg` from `docs/_themes/caravan/static/img/` as each one's replacement is actually placed, keeping `favicon.svg` and `mark.svg`, which are brand marks and not illustrations; a subject that never produced a usable candidate keeps the SVG it has today, so no page ends up worse than it is now (FR-031)

### The gate

- [X] T033 [US4] Add the weight gate step to `.github/workflows/docs-checks.yml` after the existing site build, per [contracts/weight-gate.md](./contracts/weight-gate.md): sum the apparent file sizes of the built output excluding `.doctrees`, print the figure and the remaining margin on every run, and exit non-zero above 3,000,000 bytes — with the ceiling committed in the check and no flag or environment variable able to raise or silence it (FR-029, SC-009, Principle V). Neither `du` nor the whole output directory is an acceptable measurement: they read 840 KB and 2,044 KB for a site that serves 720,306 bytes (research R1)

**Checkpoint**: the images are on the site, every one traceable to the run that made it, and the site is inside its budget

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T034 [P] Document the placement step in `scripts/imagery/README.md`: `place.py`, what it refuses and why, where records land, and that the credits page is rewritten on every placement
- [X] T035 [P] Confirm `pyproject.toml` is byte-identical to its state before this feature — no runtime dependency, no extra, no dependency group — and that installing the distribution is unchanged (FR-008, SC-006)
- [X] T036 Confirm the job in `.github/workflows/docs-checks.yml` still finishes inside the ten minutes the constitution bounds it to with the weight gate in it, measuring and printing its own duration as it already does (SC-007, FR-010)
- [ ] T037 Walk [quickstart.md](./quickstart.md) end to end, including the deliberate FR-019 refusal — a file that is not in the manifest must be refused with nothing written
- [ ] T038 Judge the set as a series (SC-008): show ten of the placed images from `docs/_static/images/` to five people, and confirm four of five say they come from one series and four of five can say what each one is about. Where they cannot, the subject goes back to another round rather than onto the page

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: no dependencies
- **Foundational (T003)**: blocks US1 and US2, because both read the aspect
- **US1 (T004–T005)**: needs T003
- **US2 (T006–T011)**: needs T003. T008 precedes T009 — a draft pass is what keeps a four-hour round from being wasted
- **US3 (T012–T016)**: T012–T015 can be confirmed against any round, including the draft; T016 needs T009
- **US4 (T017–T033)**: needs T016 for real picks, though T017–T027 can all be built before any pick exists
- **Polish (T034–T038)**: after US4

### Within User Story 4

The command is built bottom-up and must stay in this order: crop (T018) → encode (T019) → marker
(T020) → caps (T021) → record (T022) → refusals (T023) → credits (T024). T028 is a gate on the rest:
nineteen images are not placed until one has been measured.

### Parallel Opportunities

- T001 and T002 touch different files
- T025, T026 and T027 touch `docs/conf.py`, `docs/_themes/caravan/layout.html` and `NOTICE` — three
  files, no overlap, and none of them depends on `place.py` existing
- T014 and T015 are independent confirmations on the contact sheet
- T034 and T035 are independent

Everything inside `scripts/imagery/place.py` (T017–T024) is one file and must not be parallelised.

## Parallel Example: wiring the site

```bash
# Launch together — three files, no shared state, no dependency on place.py:
Task: "Add html_static_path = [\"_static\"] to docs/conf.py"
Task: "Add the AI-generated credits link to the footer in docs/_themes/caravan/layout.html"
Task: "Record the model licences and the images' CC0-1.0 in NOTICE"
```

## Implementation Strategy

### MVP

US1 alone is a deliverable: the spec says so — the subject page "is worth having even if no image is
ever rendered, because it is the written form of the art direction". Setup, T003, T004 and T005 is
the whole of it, and it costs no GPU time.

### Incremental delivery

1. Setup + Foundational → the art direction is complete and readable
2. US1 → the subjects can be argued with for free **(MVP, stop and read it)**
3. US2 → a round exists, with provenance for every candidate
4. US3 → the round is decided and `picks.yaml` exists
5. US4 → the images are on the site, inside the budget, every one disclosed and traceable

The order is not negotiable in the middle: rendering before the subjects are settled wastes a round,
and placing before picking has nothing to place.

### The two places to stop and talk

- **T028**, if a real derivative is materially heavier than the zoo's 104 KB. The margin is about
  11%; spending it is the owner's call, not the implementation's.
- **T032**, where an SVG would be retired for a subject that never rendered well. The rule is that
  the page never gets worse, so the SVG stays and the subject goes to another round.

## Notes

- No task adds a dependency, an extra or a dependency group to the distribution; T035 confirms it.
- No task adds a test file. The one check added is T033, which the owner chose in clarification.
- `place.py` writes nothing on any failure: a half-written record is worse than no record, because
  the record is the provenance.

---

## Status at close (2026-10-29)

011 closes with **the first screen and the route placed**, not the full set of nineteen. The owner
asked for a few images to get the site online first; the rest of the series waits for a later
round. What actually happened, against the plan:

- **Rendering ran in this session**, on the Spark over SSH (`dienstollama@10.123.47.52`), reusing
  the zoo's `zoo-flux` image, which carries the same dependencies as this directory's Dockerfile.
  The GB10 needs `--runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=all`; `--gpus all` fails there on a
  missing `libnvidia-egl-wayland` mount.
- **T008, the draft pass, found the art direction wrong, not the model.** The owner rejected the
  first final render because the scene made no sense (cases rolling down a road on their own, an
  "instrument board" read as a speed camera). Sixteen of the twenty prompts were rewritten so that
  each shows real things used the way they are used; a second draft confirmed every subject reads.
  Lesson recorded in the series file's history: comparisons are drawn literally ("the size of a
  matchbox" gave a matchbox; an enormous crate read as absurd).
- **The final model now renders at its native resolutions** (1664×928, 1584×1056, from the model
  card), so the 1600 px derivative is a downscale rather than an upscale (`gen.py` reads per-model
  `sizes` from the series).
- **T009 was not run in full.** One final image of the old prompts was rendered and the run was
  stopped; finals were then rendered per subject for the five places that replace the SVGs.
- **T028, measured:** real final derivatives weigh 38–85 KB an image across three widths (the zoo's
  estimate was 104 KB). The built site is 1,236,008 bytes with five images, 41% of the ceiling.
- **Placed:** the first screen (the zoo's `model-picket-forest-bench`, by owner decision — FR-003
  amended, the record carries an `origin` block), route legs 1–3, and the route page (the van,
  first rendered for the first screen). `hero.svg` and `leg-1..3.svg` are retired; **`leg-4.svg`
  stays** until the owner picks one of the two re-rendered crates (`rounds/leg4b`, seeds 396297 and
  396298) — the first was rejected as absurdly large.
- **Not done:** T009–T011 in full, T016 as a contact-sheet session (the owner judged the images
  directly), T030 for the remaining fourteen subjects, T032 for leg 4, T037–T038.
- **Beyond this feature's spec**, done on the owner's direction in the same branch: the landing
  page rewritten (hero, the YAML beside the model it builds, four pillars, route copy without
  hedging), a task table at the top of the CLI reference and a first manifest at the top of the
  manifest reference, a CLI entry in the navigation, the route pages rewritten without hedging,
  leg 2's data shipped as `_static/data/readings.csv` instead of an inline generator, leg 4's
  `sed -i` made portable to macOS, and the stylesheets versioned so a changed one is fetched.
  The documentation restructure the owner asked for next (Django-style overview, glossary,
  cross-references, split manifest reference) is feature 012.
