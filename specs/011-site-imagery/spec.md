# Feature Specification: Imagery for the site

**Feature Branch**: `011-site-imagery`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: generate the site's images rather than fetch them, with the Mobility Model Zoo's method — a series file as the art direction, a generator in a container on a CUDA machine, and two pages to decide from: a subject sheet before the render and a contact sheet after it, where the owner picks by number and downloads `picks.yaml`. Copied, not shared, like the design tokens. The same screenprint house style, but Caravan's own subjects: the route, a load that must get smaller, the gate that refuses it, the workbench, the board, the field. Twenty subjects, each with an intended place on the site, alt text and a scene description. Nothing belongs to the distribution. Every image carries its provenance. The zoo's feature 019 — records, automatic triage, derivatives, credits page, coverage check — is deliberately not ported.

## Why this feature exists

The site built in feature 010 is drawn, not photographed: five flat SVGs made by hand. They carry
the identity, and at the size of a card motif they are enough. They are not enough for the first
screen, there is no honest way to hand-draw twenty of them, and a site illustrated from two
sources at once reads as two sites — so the five give way to the series as it lands.

The Mobility Model Zoo solved the same problem and the solution is known to work on this exact
identity, because the identity is the zoo's. This feature copies the method and writes Caravan's
own subjects for it.

## Clarifications

### Session 2026-10-27

- Q: Do the generated images replace the five hand-drawn SVGs of feature 010, sit alongside them
  in a different role, or go only where no illustration exists today? → A: Replace — the generated
  images take over every place an SVG is used today and the five SVGs are retired, but no place
  loses its SVG before a picked image is placed there (FR-031).
- Q: What should the site's weight budget bound, and at what figure? → A: The whole built site
  only — the 703 KB it weighs today plus a stated allowance for the imagery, and no separate
  per-page gate. The allowance is fixed by the answer below (FR-029, SC-009).
- Q: How should a picked image get into the repository, and what enforces “no provenance, no
  placement”? → A: As the zoo does it — a placement command writes one directory per image holding
  webp derivatives at 480, 960 and 1600 px and one record file carrying the full recipe, and
  refuses an image with no manifest entry. The zoo's triage and coverage check stay unported — its
  credits page returns with the disclosure answer below — and twenty images at three widths raise
  the total ceiling to 3 MB (FR-007, FR-019, FR-020, FR-027, FR-029).
- Q: Should the site tell its readers that these images are generated, and if so where? → A: Exactly
  as the zoo does it, which is four channels and not one: the alt suffix “(AI-generated image)”, an
  IPTC `trainedAlgorithmicMedia` marker inside every derivative, a credits page generated from the
  placed records, and a footer link saying “AI-generated” on every page that shows one. This brings
  the zoo's credits page back into scope (FR-007, FR-028, FR-032, FR-033, FR-034).
- Q: Under what licence do Caravan's own generated images go out? → A: CC0-1.0, as the zoo stamps
  every one of its records, stated in each image's record and in `NOTICE` beside the model licences
  (FR-030).

## User Scenarios & Testing *(mandatory)*

The "user" here is the site's owner. Nobody else runs any of this; a reader of the site sees only
the result.

### User Story 1 - Decide the subjects before spending the GPU (Priority: P1)

The owner opens one page that lists every subject the series will render: what it is a picture of,
what sentence is sent to the model, and which page on the site it is meant for. Reading it takes a
few minutes. Changing a prompt at that moment costs nothing; changing it after a round costs the
round.

**Why this priority**: it is the only step that is cheap, and it is the one that decides whether
the expensive step produces anything usable. It also stands alone: the page is worth having even
if no image is ever rendered, because it is the written form of the art direction.

**Independent Test**: build the page from the series file and read it. Every subject has a prompt,
an intended placement and an alt text; no subject is a repeat of another; the style and negative
sentences appear once, in full, so the owner sees exactly what every image will be asked for.

**Acceptance Scenarios**:

1. **Given** the series file, **When** the subject page is built, **Then** it lists every subject
   grouped by theme, with its prompt, aspect ratio, intended placement and alt text, and states
   the style and negative sentences that are appended to all of them.
2. **Given** a subject the owner wants changed, **When** they edit the series file and rebuild,
   **Then** the page shows the change and nothing else moved.

---

### User Story 2 - Render a round (Priority: P1)

On a machine with a CUDA GPU, one command renders every subject at several seeds and writes the
images beside a manifest that records exactly how each one was made.

**Why this priority**: without it there are no images. It is P1 with story 1 rather than above it
because rendering before the subjects are settled is how a round gets wasted.

**Independent Test**: a draft run at low step count produces one file per subject per seed, plus a
manifest whose entries match the files; a second run over the same output directory renders
nothing and leaves the manifest unchanged.

**Acceptance Scenarios**:

1. **Given** a series file and an empty output directory, **When** the generator runs, **Then**
   every subject has one image per seed, each named for its theme, subject and seed, and the
   manifest has one entry per image.
2. **Given** a run interrupted half way, **When** the same command runs again, **Then** it renders
   only what is missing.
3. **Given** the same subject, seed and model, **When** it is rendered again on the same hardware,
   **Then** the image is the same.
4. **Given** a request to see what a run would do, **When** the generator is asked for a plan,
   **Then** it prints the files it would write and does not touch the GPU.

---

### User Story 3 - Pick from a contact sheet (Priority: P1)

The owner opens one page showing every candidate grouped under its subject and numbered. They
click the one they want, or say "none of these" where the subject needs another round, and
download `picks.yaml`.

**Why this priority**: the render is worthless without a way to choose from it, and a folder of
eighty PNGs is not one.

**Independent Test**: build the sheet from a rendered round and pick on it. Picks survive a reload;
the downloaded file names the chosen number for each subject and `none` for the rest.

**Acceptance Scenarios**:

1. **Given** a rendered round, **When** the sheet is built, **Then** every candidate appears under
   its subject with a number and a link to the full-size file, and each subject shows the prompt it
   was rendered from.
2. **Given** picks made on the sheet, **When** the page is reloaded, **Then** the picks are still
   there.
3. **Given** a completed sheet, **When** the owner downloads the picks, **Then** the file names one
   chosen number or `none` per subject.
4. **Given** a subject with no rendered candidate, **When** the sheet is built, **Then** it says so
   rather than omitting the subject.

---

### User Story 4 - Place a picked image on the site (Priority: P2)

A picked image is brought into the repository at the widths the pages actually use, with its
provenance, and appears on its page.

**Why this priority**: it is the point of the exercise, but it is the part that can wait: stories
1–3 produce a chosen set of images, and choosing is the work that cannot be redone cheaply. It is
also the part with the open questions below.

**Independent Test**: place one image, build the site, and check its page, its weight and its
provenance record.

**Acceptance Scenarios**:

1. **Given** a picked image, **When** it is brought in, **Then** the repository holds the
   derivatives the pages use and the record of how the image was made, and the site build serves
   it.
2. **Given** an image with no provenance record, **When** it is offered for placement, **Then** it
   is refused.
3. **Given** a placed image, **When** the site is built, **Then** the page is complete and
   understandable with images unavailable.
4. **Given** a placed image, **When** its page is built, **Then** its alt text ends with the
   disclosure suffix, the derivative carries the file marker, the credits page names the image with
   its model and licence, and the page's footer links those credits with the words "AI-generated".

---

### Edge Cases

- **A subject the model will not draw.** Some subjects survive four seeds and produce nothing
  usable. The sheet must make that visible as a state, not as an absence, and the next round must
  be able to render only those subjects with fresh seeds.
- **A render that is close but wrong in one corner.** Out of scope: there is no editing step. The
  answer is another seed or another prompt.
- **Text in the image.** The models put lettering into pictures unasked. It is in the negative
  prompt and it is the most likely reason to reject a candidate; the sheet must show candidates
  large enough to see it.
- **A GPU that is not the one this was written for.** The output is only reproducible on the same
  hardware; a different machine renders different images from the same seed. The manifest records
  which machine it was.
- **The site's weight.** The whole built site serves 703 KB today — 720,306 bytes, measured on the
  built output on 2026-10-28, not the block-rounded figure `du` reports. One render at full size is
  a significant fraction of that, and twenty are several times it.
- **A second round.** Seeds must not repeat a previous round's, or the second round re-renders the
  first round's rejects.

## Requirements *(mandatory)*

### Functional Requirements

**The art direction**

- **FR-001**: The series file MUST hold the house style as one sentence appended to every subject,
  the negative prompt, the draft and final models with their licences and model cards, and the
  subjects grouped by theme.
- **FR-002**: Each subject MUST carry an identifier unique within its theme, the prompt, the aspect
  ratio, a scene description, an alt text, and the place on the site it is intended for.
- **FR-003**: The subjects of this series MUST be Caravan's own and MUST NOT be the zoo's. A finished
  image of the zoo's MAY be placed where it shows Caravan's own subject matter: it keeps the zoo's
  record, names its origin, and is not re-rendered (owner decision, 2026-10-29: the first screen
  shows the zoo's `model-picket-forest-bench`, made for the model Caravan's own example builds). Where the zoo's style
  sentence reserves the warm accent for "the main vehicle or machine", Caravan's MUST reserve it
  for the one object the picture is about, which is the rule the site's design language already
  states for an illustration.
- **FR-004**: The series MUST carry twenty subjects, covering the first screen, the four legs of
  the route, the route index, the four concept pages, the reference pages, the budgets page, what
  is verified today, the roadmap and the board runs.
- **FR-005**: The negative prompt MUST name the clichés this subject matter attracts — glowing
  brains, circuit traces, server racks, floating interface elements — as well as the generic ones.

**Copying rather than depending**

- **FR-006**: The method MUST be a copy. No part of this feature may import the zoo, fetch from it
  at build time, or require it to be installed, and the files that were copied MUST say where they
  came from, when, and that the two may drift.
- **FR-007**: The zoo's automatic-triage and coverage machinery MUST NOT be ported in this feature.
  Its image-record shape, its derivatives and its disclosure — including the credits page — ARE
  adopted: a placed image is a directory holding its derivatives and one record file, as the zoo
  does it. Where a threshold or a setting
  exists only to feed a check that is not ported, it MUST NOT be carried over either.

**Not part of the distribution**

- **FR-008**: Nothing in this feature may add a runtime dependency, an extra or a dependency group
  to the distribution, and `pyproject.toml` MUST be unchanged by it.
- **FR-009**: No part of this feature may install anything into the project. A script that runs
  outside the container MUST declare its dependencies inline, so it runs from a throwaway
  environment. The generator MUST have its dependencies declared by the Dockerfile beside it rather
  than inline: it needs a CUDA build of torch that an inline declaration cannot deliver, and a
  declaration a script cannot satisfy is a false promise, not compliance.
- **FR-010**: The site build MUST NOT invoke any of it. The documentation CI job MUST NOT gain a
  step that needs the generator, a browser or an extra, and MUST stay inside the ten minutes the
  constitution bounds it to (SC-007). The single measurement FR-029 requires is the only growth
  permitted, and it is permitted because Principle V does not allow a budget that nothing measures.
- **FR-011**: The generator MUST run without a network connection to anything but the model host,
  and MUST need no account, token or credential.

**Rendering**

- **FR-012**: One command MUST render a whole series into one output directory.
- **FR-013**: A seed MUST be derived from the subject so that a subject keeps its seeds across runs
  and no two subjects share one, and a later round MUST be able to offset every seed.
- **FR-014**: An existing output file MUST be skipped, so an interrupted run resumes.
- **FR-015**: The run MUST be restrictable to named themes or subjects, and MUST be able to read
  the subjects of a follow-up round from a file.
- **FR-016**: A draft model MUST be selectable for checking whether the model understands a subject
  at all, at a small fraction of the time of the final model.
- **FR-017**: The generator MUST be able to print the work a run would do without touching the GPU.

**Provenance**

- **FR-018**: The manifest MUST record, per image: the model identifier and the revision actually
  loaded, its licence and model card, the complete prompt and negative prompt as sent, the seed,
  the step count, the guidance, the width and height, the series name, the date, the class of
  hardware, the container image digest, the commit of the repository and the hash of the generator
  script.
- **FR-019**: A placement command MUST be what brings a picked image in, and it MUST refuse — with a
  non-zero exit — an image that has no manifest entry. The refusal happens at placement; no standing
  site check is added for it.
- **FR-020**: The record MUST survive placement: each placed image MUST carry a record file beside
  its derivatives holding the fields of FR-018, so an image on the site remains traceable to the run
  that made it.

**The two pages**

- **FR-021**: The subject page MUST be buildable from the series file alone, with no rendered
  image, and MUST state the style and negative sentences in full.
- **FR-022**: The contact sheet MUST group candidates under their subject, number them within the
  subject, show each subject's prompt, and link each candidate to its full-size file.
- **FR-023**: The sheet MUST let the owner pick one candidate per subject or mark the subject as
  needing another round, MUST keep those choices across a reload, and MUST write them out as a file
  naming one number or `none` per subject.
- **FR-024**: The sheet MUST show a subject with no candidate as a subject with no candidate.
- **FR-025**: Both pages MUST be local files that open without a server and send nothing anywhere.
- **FR-026**: Both pages MUST be legible in the light and the dark colour scheme, and MUST use the
  site's own inks.

**Placement**

- **FR-027**: A placed image MUST be served as webp derivatives at 480, 960 and 1600 px — the widths
  the zoo uses — and MUST NOT be served at the render's own size.
- **FR-028**: Every placed image MUST carry the alt text from its subject, ending in the zoo's
  disclosure suffix “(AI-generated image)”, and every page MUST remain complete and understandable
  with images unavailable.
- **FR-029**: The built site's total weight MUST stay under 3 MB, read as 3,000,000 bytes — the
  703 KB it serves today plus an allowance of about 2.1 MB for the images at three widths, measured
  from the zoo's own records at 104 KB an image. The budget MUST be measured on the built output rather than asserted,
  exceeding it MUST fail with a non-zero exit code rather than warn, and the ceiling MUST NOT be
  raisable by a flag or an environment variable. There is no separate per-page budget.
- **FR-030**: The licence of each model used MUST be recorded where the repository records the
  licences of what it ships, and every placed image MUST itself carry CC0-1.0 — stated in its record
  and in `NOTICE` beside the model licences.
- **FR-031**: The generated images MUST take over every place the five hand-drawn SVGs of feature
  010 are used, and those SVGs MUST be retired from the site once their replacements are placed. No
  place may lose its SVG before a picked image is placed there, so a subject that never produces a
  usable candidate keeps the illustration it has today.
- **FR-032**: Every derivative MUST carry the IPTC `trainedAlgorithmicMedia` marker in its own
  metadata, written by the placement command, so the disclosure travels with the file when it leaves
  the page.
- **FR-033**: The site MUST carry a credits page naming, for each placed image, its scene, the
  model, the model's licence, the date and the class of hardware, and it MUST say “AI-generated” on
  it. The page MUST be written from the records by the placement command and committed like any
  other page, not generated by the site build, so FR-010 holds. Regenerating it on every placement
  is what keeps it from drifting, so no standing check guards it either (FR-019).
- **FR-034**: Every page that shows a generated image MUST link that credits page from its footer,
  and the link text MUST contain “AI-generated”.

### Key Entities

- **Series**: the art direction. One house style, one negative prompt, two models, and the subjects
  grouped by theme. The file a reviewer reads to know what the pictures will be.
- **Subject**: one picture to be made. Identifier, prompt, aspect, scene, alt text, intended
  placement, and whether it is held in reserve.
- **Round**: one rendering of a series. A directory of images and the manifest that says how each
  was made.
- **Candidate**: one image in a round — one subject at one seed. Numbered within its subject on the
  sheet; that number is what a pick names.
- **Picks**: the owner's decision. One chosen number or `none` per subject.
- **Placement**: a picked image brought into the repository as the zoo brings one in — one directory
  per image holding its webp derivatives at 480, 960 and 1600 px and one record file with the recipe
  of FR-018, the model's licence, its own CC0-1.0 licence, the alt text and the pages it appears
  on.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The owner can read the whole series — twenty subjects, their prompts and their
  intended places — in under ten minutes, before any GPU time is spent.
- **SC-002**: One command renders a complete round unattended, and an interrupted run resumes
  without re-rendering anything it already produced.
- **SC-003**: After one round, at least fifteen of the twenty subjects have a candidate the owner
  is willing to place.
- **SC-004**: The owner can decide a complete round — one pick or a `none` for every subject — in
  under thirty minutes at the sheet.
- **SC-005**: Every image that reaches the site can be traced to the exact recipe that made it,
  and re-rendering from that recipe on the same hardware reproduces it.
- **SC-006**: Installing the distribution is unchanged by this feature: the same dependency count,
  the same extras, the same install time and size.
- **SC-007**: The documentation CI job stays inside the ten minutes the constitution bounds it to.
- **SC-008**: Shown ten of the images, four of five people say they come from one series, and four
  of five can say what each one is about.
- **SC-009**: The built site stays under 3,000,000 bytes with every placed image in it, measured on
  the built output as the sum of the files it serves.

## Principles this touches

The constitution asks every spec to name the principles it touches and say how it complies.

- **III. Reproducible by Construction**: every image carries the recipe that made it (FR-018), seeds
  are derived from the subject and recorded, and the one place reproduction breaks — different
  hardware from the same seed — is documented rather than implied, with the hardware class recorded
  per image.
- **IV. Measured, Emulated or Estimated**: this feature reports one figure, the site's weight, and
  it is measured on the built output rather than asserted (FR-029). The disclosure rules
  (FR-028, FR-032–034) are the same instinct applied to a picture: what made it travels with it.
- **V. Budgets Are Gates, Not Warnings**: the weight budget states a number, measures it, fails with
  a non-zero exit rather than warning, and cannot be raised by a flag or an environment variable.
- **VIII. No Lock-In, Local Execution**: local GPU, no account, no token, no hosted service
  (FR-011).
- **XI. No Claude in Model Learning or Extraction**: the images come from FLUX.2-klein-4B and
  Qwen-Image-2512 — no Claude model in the path — and they are site decoration that never becomes
  model input data. The manifest records the producing model per image, so a Claude model would be
  visible and would fail the gate. This principle admits no deviation and none is sought.
- **XII. Small Core, Few Dependencies**: `pyproject.toml` is untouched — no runtime dependency, no
  extra, no dependency group (FR-008). Copying a few hundred readable lines instead of depending on
  the zoo is what this principle asks for.
- **Project Scope & the Zoo**: copied, not shared (FR-006). Nothing imports the zoo, fetches from it
  or needs it installed, and no zoo model code, dataset or credential is carried.
- **Resources & Cost Discipline**: local compute, the first tier the constitution asks for, at no
  cash cost — so no cash budget is required — and no credential is read or written.

## Assumptions

- The owner has a machine with a CUDA GPU and can run containers on it. This session cannot: the
  Spark is behind a VPN it cannot reach and the container it runs in has no GPU, which is why the
  rendering steps of this feature are written to be run elsewhere.
- Both models are Apache-2.0 and ungated, and no account or token is needed to fetch them.
- A full round is roughly eighty images at about three minutes each — call it four hours of GPU
  time, and it is unattended. That is local compute, which is the tier the constitution asks for
  first, and it costs no cash.
- Images are reproducible on the same hardware with the same seed, and not across different
  hardware.
- The hand-written design language of feature 010 — four inks, the accent reserved for the subject
  of a picture, flat fields and hard edges — is the art direction, and this feature does not revisit
  it.
- A draft of the series file, the generator, the Dockerfile and both pages already exists on this
  branch under `scripts/imagery/`. It is a starting point for the plan, not a decision the plan has
  to accept.
- This branch is cut from `010-website-overhaul` rather than from `main`, because the pages these
  images are meant for exist only there. It merges after 010 does.

## Out of scope

- The triage half of the zoo's feature 019: automatic rejection by face, text, palette and
  near-duplicate checks, the coverage check and the pool overview — about 520 of its 1,600 lines,
  built for a hundred-odd images across many themes. At twenty subjects the owner looks
  at every candidate, which is what the automatic rejection exists to avoid at the zoo's scale. If
  the library grows past what one person will look at, port it then. Its image records as
  directories, its generated derivatives and its disclosure — alt suffix, file marker, credits page
  and footer link — are **not** out of scope; see FR-007, FR-027 and FR-032 to FR-034.
- Editing or retouching a render.
- Any image that is not generated: no stock photography, no fetched asset.
- Photographs of real hardware. Those are a different kind of claim, and Principle IV governs them.
