# Feature Specification: A website that teaches Caravan in half an hour

**Feature Branch**: `010-website-overhaul`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "überarbeite die Webseite. Sie ist hässlich und nicht gut zu lesen. Zudem für Marketing-Zwecke ungeeignet. Das oberste Ziel ist: ein leichter Einstieg in das Thema. Nutzer sollten innerhalb von 3 Sekunden verstehen was der Vorteil ist und warum sie Caravan nutzen sollten. Nach 15 Minuten haben sie erfolgreich ein Modell gebaut. Nach 30 Minuten deployed. Erstelle dafür eine Tutorial-Reihe. Nenne sie aber nicht Tutorial, das klingt zu langatmig und abgedroschen. Die Tutorials von Django (Python) sind für mich immer ein gutes Beispiel. Am Ende eines jeden Schritts hat man was Zählbares. Die Seite braucht ein Design und eine Metapher-Sprache. Ich dachte so an 8-Bit, aber professionell und nicht übertrieben. Da wir ja auf limitierter Hardware arbeiten. Bin offen für Gegenvorschläge. Nimm das LoRa-Board raus. Das war ein persönliches Problem, das die KI in die offene Seite eingearbeitet hat. Verweise nicht auf Spec-Kit-Artefakte. Das interessiert die Nutzer nicht. Erkläre. Wir verwenden Abkürzungen wie MLP. Was soll das sein? Warum das? Erkläre auch Einstellungen. Momentan sind da hässliche Tabellen. Viel zu wenig Inhalt, viel zu hässlich."

## Decisions taken

Three questions were put to the owner on 2026-10-27 and answered the same day.

- **D1 — Restrained 8-bit, spoken as a journey.** The visual register is 8-bit; the verbal register
  comes from the project's own name. Chosen over literal retro-computing and over datasheet
  austerity, because the 8-bit register earns its place twice — it is what int8 arithmetic and a
  few kilobytes of RAM actually look like — while the journey gives the series its shape without
  borrowing any retro vocabulary. Carried by FR-026, FR-027 and FR-008.
- **D2 — The board withdrawal reaches the site only.** Every mention of the owner's personal
  development board comes off the site. Its firmware example and the pre-release firmware build for
  it stay in the repository as the owner's own verification, unmentioned by the site. Carried by
  FR-035.
- **D3 — The deployment leg targets a generic ESP32 development board.** Already a registered
  export target, widely available, inexpensive, and on the toolchain the project already uses.
  Carried by FR-037.

**A consequence D3 creates, recorded here rather than discovered in planning.** D2 keeps the only
firmware build the pipeline has, and that build is for the withdrawn board. So nothing yet verifies
the path the site will teach. FR-038 makes closing that gap part of this feature; which check closes
it is a planning decision.

## Context: what is wrong today

The site is thirteen pages built from `docs/`, in a default theme, written as a precise record for
someone who already knows what Caravan is. Four concrete failures follow from that:

- **No verdict on arrival.** The landing page opens with a one-line definition, then a bulleted
  account of what the manifest names, then a paragraph headed "What it is not". A visitor learns
  what the thing *is* long before learning why they would want it, and the first thing stated
  emphatically is what it refuses to do.
- **The entry path is one long page.** `try-it.md` is a single 93-line run of commands ending in a
  32-item list of output files. Nothing is finished until everything is finished, and a reader who
  stops halfway has nothing.
- **Reference pages tabulate instead of explaining.** The manifest reference is six-column tables
  (field, type, default, allowed, read by, rules) whose cells carry link clusters such as
  `CF-9, CF-11, CF-13, DS-12`. `mlp` and `conv1d` appear as values a field accepts; neither the
  words behind them nor the choice between them is explained anywhere on the site.
- **One person's hardware became the project's public face.** A specific hobby development board
  is named on eight of the thirteen pages, in the release notes, and in the only guide that gets a
  model onto hardware.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The three-second verdict (Priority: P1)

An embedded developer follows a link to the site. They have a CSV of sensor readings, a
microcontroller on their desk, and a vague intention to put a small model on it. They have also
seen four other projects this week. Before they scroll, before they read a sentence twice, they
want to know: does this thing solve my problem, and what does it cost me to find out?

The first screen answers that: what Caravan does for them, what it demands of them, what it will
not do, and one way in that is obviously short.

**Why this priority**: It is the user's stated top goal and the gate on everything else. A visitor
who leaves in three seconds never reaches the series, however good the series is. It also ships
alone: a landing page that lands is worth having before any other page is touched.

**Independent Test**: Show the first screen to people who do not know the project for five
seconds, take it away, and ask what it does, who it is for, and what it refuses to do. Can be
tested with the new landing page alone, the rest of the site untouched.

**Acceptance Scenarios**:

1. **Given** a visitor who has never heard of Caravan, **When** they see the first screen for five
   seconds on a laptop, **Then** they can state in their own words what Caravan produces and from
   what, without having scrolled.
2. **Given** that same visitor, **When** they are asked what Caravan will not do, **Then** they can
   name at least one boundary, and they did not meet that boundary before learning the benefit.
3. **Given** a visitor who wants to start, **When** they look for the way in, **Then exactly one**
   next step is offered as primary, with the time it takes stated next to it.
4. **Given** a visitor on a phone, **When** the page opens, **Then** the verdict and the primary
   next step are both visible without scrolling and without sideways scrolling.

---

### User Story 2 - A model of my own inside fifteen minutes (Priority: P1)

A developer takes the way in. They work through short steps, each of which ends with something
they can point at: a file on disk, a number, a verdict. Within fifteen minutes at the keyboard
they have trained and quantized a model — first the worked example, then the same pipeline reading
columns they chose themselves — and they know what each artifact is for.

**Why this priority**: The second half of the user's stated goal, and the moment the project earns
trust. It is independently valuable: the series can ship while the reference pages are still being
rewritten.

**Independent Test**: Hand a developer a clean machine and the URL, start a timer, and record the
wall-clock time at which an int8 model file first exists, and again when one exists that reads
their own columns. No hardware needed.

**Acceptance Scenarios**:

1. **Given** a reader at the end of the first step, **When** they are asked what they have,
   **Then** they can name a concrete artifact or number produced by that step alone, and the step
   said in advance that this would be the result.
2. **Given** a reader who stops after any step, **When** they close the page, **Then** what they
   built still works and still means something; no step leaves a half-configured state.
3. **Given** a developer starting from a clean machine with the install already done, **When** they
   follow the series without detours, **Then** an int8 model exists within fifteen minutes.
4. **Given** that developer, **When** they reach the step that uses their own data, **Then** they
   change their columns in one named place and re-run one command, and the site told them which
   earlier results that invalidates.
5. **Given** a reader whose own data makes the quantization gate fail, **When** the run stops,
   **Then** the series anticipated this, explains what the gate measured, and gives the next move;
   the reader is not stranded on a red error.
6. **Given** a reader on a Python version the training extra does not support, **When** they reach
   the first step, **Then** the series says so before the install command, not after it fails.

---

### User Story 3 - On hardware inside thirty minutes (Priority: P2)

The same developer continues: the exported C files go into a firmware project, the board runs the
model, and its answers are checked against the same model's answers on their computer. Thirty
minutes after arriving, a microcontroller is answering, and they know whether to trust it.

**Why this priority**: The second number the user named, and the claim that separates Caravan from
a model-training script. It is P2 only because it depends on hardware the reader may not have, so
it cannot be the first thing built.

**Independent Test**: Continue the timed run from User Story 2 on the chosen hardware and record
when the board first answers, and whether its answers agreed with the host's. The no-hardware path
is tested separately by following the same step without a board.

**Acceptance Scenarios**:

1. **Given** a reader with the supported hardware and its toolchain installed, **When** they follow
   the deployment step, **Then** the board answers test windows within fifteen minutes of finishing
   User Story 2.
2. **Given** a board that has answered, **When** the reader compares its answers with their
   computer's, **Then** the site tells them what agreement to expect and what a disagreement means.
3. **Given** a reader with **no** hardware at all, **When** they reach this step, **Then** a path is
   offered that still ends in something countable, and it is clear which claims that path cannot
   support.
4. **Given** any figure about the board on this page, **When** it is shown, **Then** it carries one
   of the three provenance labels (`estimated`, `emulated`, `measured`), and no timing figure is
   labeled `measured` without a physical board behind it.

---

### User Story 4 - I understand what I am choosing (Priority: P2)

A reader has a working model and starts changing it. They meet `mlp`, `conv1d`, `zscore`,
`most_common`, `accuracy_drop_max`, `embedding_size`. For each, the site tells them what the words
mean, what the setting does to the model, when they would want to change it, and what happens if
they get it wrong — in prose they can read, not as a cell in a table.

**Why this priority**: The user's most repeated complaint ("Erkläre."). It converts a reader who
copied an example into someone who can build their own model, but it only matters once they have
run the example.

**Independent Test**: Take every abbreviation and every setting on the site, and check that each
has a plain-language definition at first use and an explanation of the choice. Testable page by
page, with no pipeline run needed.

**Acceptance Scenarios**:

1. **Given** any abbreviation on any page (`MLP`, `CNN`, `int8`, `RAM`, `CSV`, `MAE`), **When** it
   first appears on that page, **Then** it is expanded and explained in one sentence a reader
   outside machine learning can follow.
2. **Given** a reader choosing a model template, **When** they look it up, **Then** the site says
   what shape of data each template suits, what it costs in memory, and which to pick for the data
   they described — not only that the field accepts two values.
3. **Given** any setting a reader can write in the manifest, **When** they look it up, **Then** they
   find what it does, why the default is the default, when to change it, and what goes wrong at the
   extremes.
4. **Given** a reader who wants to look up one field quickly, **When** they open the reference,
   **Then** they can still find it in a scannable form; the explanations did not replace the
   lookup, and the lookup no longer carries unexplained rule codes as its only detail.

---

### User Story 5 - The public face is the project's, not one person's (Priority: P3)

A visitor reads the site end to end and meets nothing that belongs to the author's private
projects, and no trace of how the project is built internally: no spec folders, no feature numbers,
no planning artifacts. What is left is Caravan, its hardware story, and what a reader can do.

**Why this priority**: Explicitly asked for, cheap to verify, and it protects the credibility the
first four stories build. It is P3 because the site works without it.

**Independent Test**: Search the built site for the removed board's names and for internal
artifact references; both return nothing. Check that no page lost a claim it needed.

**Acceptance Scenarios**:

1. **Given** the published site, **When** it is searched for the names of the withdrawn board,
   **Then** there are no matches on any page.
2. **Given** a page that previously rested on that board for a claim, **When** it is read now,
   **Then** the claim is either carried by the hardware the site does support, or stated as not yet
   verified — never silently dropped while the conclusion stays.
3. **Given** the published site, **When** it is searched for internal development artifacts (spec
   directories, feature numbers, planning and task files), **Then** there are no matches, and every
   statement that cited one now stands on something a reader can see.
4. **Given** a reader who wants to know how far a claim is verified, **When** they look,
   **Then** that is still answerable from the site; removing the internal citations did not remove
   the provenance.

---

### User Story 6 - One design, readable everywhere (Priority: P3)

Every page of the site looks like the same project made it, carries a consistent visual and verbal
metaphor, and is comfortable to read: on a phone, on a wide screen, in dark mode, at 200% zoom, and
with a screen reader.

**Why this priority**: It is the frame the other stories are delivered in rather than a deliverable
of its own, and the first screen can prove the direction before the whole site adopts it.

**Independent Test**: Audit each page against the stated design rules and against accessibility
checks, on a phone and a desktop, in both colour themes.

**Acceptance Scenarios**:

1. **Given** any two pages, **When** they are seen side by side, **Then** they share one type scale,
   one palette, one treatment of code, and one voice.
2. **Given** any page, **When** body text is measured, **Then** its contrast meets the AA level of
   the published accessibility guidelines in both light and dark themes, and line length stays in a
   comfortable range for reading.
3. **Given** a reader at 200% zoom on a phone-width window, **When** they read any page, **Then**
   nothing is clipped and nothing scrolls sideways — including code blocks and tables.
4. **Given** a reader using a screen reader or keyboard only, **When** they move through a page,
   **Then** headings are ordered, every image has a text alternative, and no information is carried
   by colour alone.
5. **Given** the metaphor the site adopts, **When** a reader meets it, **Then** it carries meaning
   about the subject (small models, tight budgets, constrained hardware) and never decorates at the
   cost of legibility.

---

### Edge Cases

- **The install dwarfs the lesson.** The training dependency is around 1.9 GiB. On a slow
  connection the download alone can exceed the fifteen-minute promise. The series must state the
  weight and the expected wait before the reader commits, and the fifteen-minute claim must be
  defined against a measurable, honest start line.
- **A reader on an unsupported Python version.** Training needs one specific version; validation
  and rendering work on more. The series must branch before the install, and the branch that cannot
  train must still end in something countable.
- **A reader on Windows.** The current entry path is written for Linux and macOS only. Either
  Windows is supported in the series or it is named as unsupported on the way in, before the reader
  has spent anything.
- **A reader with no microcontroller.** The thirty-minute promise assumes hardware on the desk. The
  deployment step must have a no-hardware path that is honest about what it does not prove.
- **The reader's own data fails the gate.** A failing budget is a correct outcome, not a bug. The
  step that uses their own data must treat it as a lesson with a next move.
- **The reader's data is unlike the example's.** Wrong column types, one class, a tiny file, no
  header row. The step must say which of these the pipeline will refuse and how the reader will
  recognise it.
- **A number loses its evidence.** Removing the board that produced a figure must remove the figure
  or relabel it, never leave it standing with its provenance deleted.
- **The series and the software drift apart.** Commands and version numbers in the series will rot
  silently. Something must fail when the series stops matching the software it teaches.
- **Deep links break.** Existing pages are linked from release notes and from outside. Renaming or
  merging pages must not leave the old addresses dead without a forward.
- **No pictures.** The site must stay legible and complete with images disabled or unloaded.

## Requirements *(mandatory)*

### The landing page

- **FR-001**: The first screen MUST state, in the reader's language and before any scrolling, what
  Caravan takes as input, what it produces, and which hardware that output runs on.
- **FR-002**: The first screen MUST name the cost of entry — what the reader must bring (their own
  tabular data, a supported Python version) — and the install weight MUST be discoverable before
  the reader runs an install command.
- **FR-003**: The first screen MUST offer exactly one primary next step, labeled with the time it
  takes, and that step MUST be the first part of the series.
- **FR-004**: Caravan's boundaries MUST remain stated on the landing page, but MUST appear after the
  benefit and MUST be phrased as scope rather than as refusals.
- **FR-005**: The landing page MUST NOT require the reader to understand the pipeline's internal
  stage names in order to understand the benefit.
- **FR-006**: Every claim on the landing page MUST be checkable somewhere on the site, and any
  figure about hardware behaviour MUST carry its provenance label where it appears.

### The series

- **FR-007**: The site MUST carry a series of ordered, short parts that takes a reader from nothing
  to a deployed model, replacing the single long entry page.
- **FR-008**: The series MUST NOT be called a tutorial, a walkthrough, or "getting started". Its
  parts MUST be called **legs**, numbered, their vocabulary that of FR-026, and each leg's title
  MUST name what the reader ends it with — so that a title read on its own says what the leg is
  worth, in the shape of Django's "Writing your first app, part N".
- **FR-009**: Each part MUST declare, before its first instruction, what the reader will have at the
  end of it and roughly how long it takes.
- **FR-010**: Each part MUST end with a named, countable result the reader can verify themselves —
  a file that now exists, a number the run printed, a verdict the pipeline reached — and MUST show
  the reader how to confirm it.
- **FR-011**: Each part MUST leave the reader's work in a usable state; no part may depend on a
  later part to be meaningful.
- **FR-012**: The parts MUST be ordered so that an int8 model exists at or before the fifteen-minute
  mark and a model is running on hardware at or before the thirty-minute mark, both measured from
  the start of the first part.
- **FR-013**: Each part MUST end by naming the next part and what it adds, and MUST offer a way out
  for a reader who stops there.
- **FR-014**: The series MUST explain each artifact at the moment the reader first has it, rather
  than listing every output file at the end.
- **FR-015**: The part that introduces the reader's own data MUST state which earlier results that
  invalidates and which command re-establishes them.
- **FR-016**: The series MUST handle the known dead ends in place: an unsupported Python version, a
  failing quantization gate, missing hardware, and data the pipeline will refuse.
- **FR-017**: The commands, filenames and version strings the series shows MUST be verified against
  the software automatically, so that a release which breaks them fails a check rather than
  shipping a series that lies.

### Explaining the subject

- **FR-018**: Every abbreviation on every page MUST be expanded at its first use on that page and
  explained in one sentence that assumes no machine-learning background.
- **FR-019**: The site MUST carry an explanation of each model template — what the abbreviation
  stands for, what kind of data it suits, what it costs in memory and flash, and how to choose
  between the available templates for a described dataset.
- **FR-020**: Every manifest setting a reader can write MUST have prose that states what it does,
  why its default is the default, when a reader would change it, and what goes wrong at its
  extremes.
- **FR-021**: Reference pages MUST remain usable for quick lookup, but a lookup entry MUST NOT
  consist only of type, default and rule codes; each MUST link to or carry its explanation.
- **FR-022**: Rule identifiers MUST NOT be the primary content of a reference entry. Where a rule is
  named, the site MUST say in words what the rule rejects and what a reader should do instead.
- **FR-023**: The site MUST explain the quantization gate and the fit check as concepts — what they
  measure, why they stop a run, and how a reader chooses their budgets — not only as fields.
- **FR-024**: Concept explanations MUST be reachable both from the series, at the moment the concept
  first matters, and from the reference, without duplicating the explanation in two places that can
  drift apart.
- **FR-025**: Where the site uses a term from another project's vocabulary because Caravan borrowed
  it, it MUST say so once and explain the term in its own words.

### Design and metaphor

- **FR-026**: The site MUST adopt one design and metaphor language, applied to every page (D1):
  a **restrained 8-bit visual register** — a visible grid, a small fixed palette, pixel-exact
  figures, monospace wherever a number or a command is shown — and a **verbal register drawn from
  the project's own name**, in which the reader travels a route in numbered legs and what a board
  can carry is its budget.
- **FR-027**: The 8-bit register MUST stay a register and not a costume. Period pastiche — scan
  lines, simulated screen curvature, blinking cursors, decorative glitch, pixel type in body text —
  MUST NOT appear. Where a reader could take the register for nostalgia, the site MUST say once, in
  its own words, what it stands for: int8 is the arithmetic every exported model is reduced to, and
  a few kilobytes is what a board really has.
- **FR-028**: The design language MUST be written down with enough precision that a later page can
  be made to match it without guessing: the type scale, the palette with its contrast figures, the
  treatment of code, tables and figures, and the voice.
- **FR-029**: Legibility MUST take precedence over the metaphor wherever the two conflict, and the
  written design language MUST say so.
- **FR-030**: Body text MUST meet the AA contrast level of the published accessibility guidelines in
  both light and dark themes, and the site MUST honour the reader's system preference for theme.
- **FR-031**: Every page MUST be usable at phone width and at 200% zoom with no sideways scrolling
  and nothing clipped, including code blocks and tables.
- **FR-032**: Information MUST NOT be carried by colour alone, every image MUST have a text
  alternative, and heading levels MUST be ordered on every page.
- **FR-033**: The site MUST remain complete and legible with images unavailable.
- **FR-034**: Tables MUST be used only where a reader genuinely scans across columns to compare,
  and MUST be readable at phone width; dense multi-column tables MUST NOT be the carrier of
  explanation.

### What comes off the site

- **FR-035**: Every reference to the withdrawn development board MUST be removed from the site
  (D2): its guide, the pages that mention it, the example manifest's comments, and the release
  notes. The withdrawal reaches the site only — the firmware example project and the pre-release
  firmware build for that board stay in the repository as the owner's own verification, and the
  site MUST NOT mention either.
- **FR-036**: Where a claim rested on that board, the claim MUST be re-grounded on the hardware the
  site still supports or MUST be restated as not yet verified; no conclusion may keep standing
  after the evidence under it is removed.
- **FR-037**: The deployment leg MUST be written for a **generic ESP32 development board** (D3):
  a registered export target, widely available, and on the toolchain the project already uses. The
  leg MUST name the board it was written against, and MUST say what a reader holding a different
  ESP32 board has to change.
- **FR-038**: What the deployment leg tells a reader to do MUST be verified before a release by a
  check that exercises that same path. The firmware build which exists today covers the withdrawn
  board (D2) and therefore does not cover this one; the gap MUST be closed rather than recorded.
- **FR-039**: The site MUST NOT reference the project's internal development artifacts — spec
  directories, feature numbers, plan, task or analysis files — on any page a reader sees.
- **FR-040**: Where such a reference carried evidence for a claim, the claim MUST be supported from
  the site itself or dropped with its conclusion; the provenance of every retained hardware figure
  MUST survive the removal.
- **FR-041**: Removal MUST NOT create dead addresses: every page that is renamed, merged or deleted
  MUST either keep its address or forward from it.

### Keeping it true

- **FR-042**: The site MUST continue to fail its build on a broken link, a broken anchor, or a page
  that no navigation reaches.
- **FR-043**: The site MUST state which Caravan version it describes on every page.
- **FR-044**: The site's own build and checks MUST NOT add a runtime dependency to the Caravan
  package, and MUST NOT require any hosted service to build locally.
- **FR-045**: A change that touches only the site MUST NOT trigger the code test matrix.
- **FR-046**: The site MUST be buildable and viewable offline on a developer's machine with no
  accounts and no keys.

### Key Entities

- **The landing page**: the three-second verdict. Carries benefit, cost of entry, scope, and one
  primary next step.
- **A part of the series**: one ordered step. Has a stated duration, a promised countable result, the
  instructions, the verification of the result, and a pointer to the next part.
- **A concept explanation**: one idea a reader must hold to make a choice (a template, a
  normalization, a gate, a budget). Written once, reachable from both the series and the reference.
- **A reference entry**: one manifest field or one command. Carries the scannable facts for lookup
  and the explanation of the choice, with the rules stated in words.
- **The design language**: the written rules every page is made to match — type, palette with
  contrast figures, code and table treatment, the metaphor and its limits, and the voice.
- **A hardware claim**: a figure about behaviour on a board, inseparable from its provenance label
  and the board, firmware and toolchain behind it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a five-second exposure test with at least five people who do not know the project,
  at least four can state what Caravan produces and from what, and at least four can name one thing
  it does not do.
- **SC-002**: In the same test, every participant can point to the single intended next step.
- **SC-003**: Of five developers given a clean machine and the URL, at least four reach an existing
  int8 model file within fifteen minutes of starting the first part, with the install already done,
  and the install's download weight and expected wait were stated to them before they ran it.
- **SC-004**: At least four of those five reach a model answering on the supported hardware within
  thirty minutes of the same start, counting only those who had the hardware and its toolchain
  ready.
- **SC-005**: Every part of the series ends with a result the reader verified themselves; in a
  read-through of all parts, none ends without a stated, checked outcome.
- **SC-006**: No reader in the timed runs needs a source outside the site to finish a part.
- **SC-007**: Every abbreviation on the site is expanded and explained at its first use on its page;
  an audit of all pages finds no unexplained abbreviation.
- **SC-008**: Every manifest setting a reader can write has prose covering what it does, why the
  default, when to change it, and what breaks at the extremes; an audit against the full field list
  finds no gaps.
- **SC-009**: A reader can choose between the model templates from the site alone: given three
  described datasets, four of five readers pick the template the site's own guidance implies.
- **SC-010**: A search of the published site for the withdrawn board's names returns no matches, and
  every claim that rested on it is either re-grounded or restated as unverified.
- **SC-011**: A search of the published site for internal development artifacts returns no matches,
  and every hardware figure that remains still carries its provenance label.
- **SC-012**: Every page meets the AA contrast level in both themes, is free of sideways scrolling
  at phone width and 200% zoom, has ordered headings, and has a text alternative for every image.
- **SC-013**: No address that worked before the overhaul returns nothing afterwards.
- **SC-014**: A deliberate break — a stale command, a wrong version string, a dead link, an
  unreachable page — fails the site's checks rather than publishing.
- **SC-015**: The site builds and is readable offline from a clean checkout, with no accounts and no
  network beyond fetching its build tools.
- **SC-016**: No hardware figure appears anywhere on the site without exactly one provenance label,
  and no timing figure is labeled as measured without a physical board, firmware and clock recorded
  behind it.

## Assumptions

- **The audience** is an embedded or data-adjacent developer who can run a terminal and has, or can
  obtain, a CSV of their own. Not a machine-learning practitioner: that is the point of the
  explanations.
- **The fifteen-minute clock** starts when the reader begins the first part with the install already
  complete, and excludes the dependency download, whose weight and expected wait are stated before
  the reader commits. The thirty-minute clock starts at the same point and assumes the board's
  toolchain is already installed. Both are measured as a median over at least five runs on a
  machine of ordinary speed.
- **The reader's language is English**, as the site is today. This request was written in German;
  translating the site is not part of it.
- **The documented pipeline does not change.** This is a change to how Caravan is presented and
  explained. Any defect in the software the writing uncovers is reported, not fixed here; any
  change to a command's behaviour is out of scope.
- **The example dataset stays** as the series' starting point, so that the first part can finish in
  minutes without the reader supplying anything.
- **The existing checks stay** the floor: warnings as errors, no orphan pages, no broken anchors.
  The overhaul adds to them and removes none.
- **The release workflow keeps publishing the site**, from the same source directory, on the same
  address.
- **The metaphor decides the vocabulary, not only the look.** D1 was taken as one decision because
  the series' parts are named out of it; "leg" is therefore a term the whole site owes consistency
  to, and the pipeline's own "stage" keeps its separate meaning.
- **The deployment leg starts from what the export already writes.** Every run produces a runner
  skeleton for each declared target, the ESP32 among them. The leg is expected to build on that
  rather than on a second example project, which is what makes thirty minutes plausible; whether
  the skeleton is enough as it stands is for planning to establish.
- **The site is written for one ESP32 board and says so.** Readers hold many variants; the leg names
  the one it was written against instead of pretending to cover all of them (FR-037).
- **The provenance discipline of the project applies to the site**: a marketing page is a published
  table for this purpose, so no hardware number loses its label for the sake of a cleaner headline.
- **"MLP" is multilayer perceptron and "conv1d" a one-dimensional convolutional network.** The site
  does not have to keep these names for its own explanations, but the manifest field values are the
  software's and are not changed here.
