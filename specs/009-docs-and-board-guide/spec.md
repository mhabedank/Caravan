# Feature Specification: Documentation Site and the First Model on a Board

**Feature Branch**: `009-docs-and-board-guide`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "Documentation on GitHub Pages: landing page, CLI reference, manifest
(YAML) reference, compatibility, roadmap. * End-to-end guide for the LILYGO LoRa32: from export
onto the board, with output on the OLED."

## Context

`v0.1.0rc2` is released. Every stage from manifest to C array exists. What is missing is the two
things the owner needs before the next candidate. In the owner's words (2026-10-26): "eine komplette
Dokumentation … eine kleine Landingpage, dann Dokumentation der Schnittstelle, also wie funktioniert
die CLI, wie funktioniert das [YAML]-Format, was sind momentan die Kompatibilitäten … und was wird in
Zukunft gehen", followed by "ein, zwei kleine Projekte … Ende zu Ende wirklich bis auf den
Mikrocontroller drauf, um zu sehen, dass das auch wirklich so klappt". This is the goal of
`v0.1.0rc3`.

Today the documentation is scattered:

- the README;
- `docs/try-it.md`;
- `docs/manifest-changes.md`;
- `docs/roadmap.md`;
- the contracts under `specs/`, written for the people who built each feature rather than for
  someone using it.

No page lists every command and option, or every manifest field with its default and the rules
that check it.

No exported model has ever run on a microcontroller. The runner skeleton the export writes says so
itself: "Emitted and never compiled." The ESP32 has no emulator in the verification ladder (the
board description records this), so the next rung for it is the physical board.

The owner has a LILYGO LoRa32 at hand: an ESP32 with a small OLED. That matches Caravan's existing
`esp32` board description. The owner chose PlatformIO to build and flash. The board revision is
not yet known, and it decides the OLED pins.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run an exported model on the LoRa32 and see its answers on the OLED (Priority: P1)

The author follows one guide:
- from an empty directory, through `caravan export` of the example model;
- to a firmware project built and flashed onto a LILYGO LoRa32.

The board then runs the model on a handful of windows from the test part. For each window, the
OLED shows the model's answer, the expected answer and whether the board agrees with the host. The
same lines go to the serial port.

**Why this priority**: It is the claim the whole pipeline rests on and the one thing never shown:
that what Caravan exports runs on a microcontroller and gives the answers the host measured. It is
also the owner's stated test of the framework. Every defect it finds is a defect of Caravan, found
before rc3 rather than by a user.

**Independent Test**: On a LoRa32 with nothing else installed, follow the guide word for word.
Check that the OLED (or, without one, the serial output) shows one line per window, and that the
board's decision equals the host reference's decision for every window.

**Acceptance Scenarios**:

1. **Given** the example manifest and the synthetic fixture, **When** the author follows the guide
   through export, build and flash, **Then** the board starts, runs every shipped window, and shows
   per window the decision, the expected class and whether it agrees with the host reference.
2. **Given** the board has run all windows, **When** the author reads the summary line, **Then** it
   states how many windows agreed with the host reference out of how many were run.
3. **Given** a board revision whose OLED pins differ from the default, **When** the author follows
   the guide's pin table, **Then** they change one stated setting and the OLED works. The guide
   tells them how to recognise their revision.
4. **Given** the OLED stays dark (wrong pins, no display), **When** the author opens the serial
   monitor, **Then** the same results are there, so the model's behaviour can be checked without
   the display.
5. **Given** the arena configured in the firmware, **When** the model has been initialised, **Then**
   the board reports the arena the runtime actually used, labeled as measured on the named board.
   The guide shows how to set the arena from that figure.
6. **Given** the guide's firmware project and a fresh Caravan release candidate, **When** the
   release is prepared, **Then** the firmware is built for the ESP32 automatically, and a failure
   to build blocks the release.

---

### User Story 2 - Find out how to use Caravan from one site (Priority: P1)

A reader who has never seen Caravan opens the documentation site. They learn:
- what Caravan is and is not;
- how to install it;
- what each command does;
- how to write a manifest.

They never have to read a spec or the source.

**Why this priority**: The owner named it first. Without it, the owner's own projects (Story 3)
depend on remembering conversations rather than on a document. A tool whose interface is described
only in its source is not usable by anyone but its authors.

**Independent Test**: Starting at the landing page, find:
- the meaning of every option of `caravan export`;
- the default of `preprocessing.split.probabilities`;
- what rule CF-14 checks.

Each answer is on a page reached from the landing page.

**Acceptance Scenarios**:

1. **Given** the landing page, **When** a reader looks for the CLI reference, the manifest
   reference, the compatibility page, the roadmap and the board guide, **Then** each is linked from
   the landing page.
2. **Given** the CLI reference, **When** a reader looks up any command, **Then** they find:
   - its purpose;
   - every argument and option with its meaning;
   - what it reads and writes;
   - its exit codes, distinguishing a failed gate from a crash.
3. **Given** the manifest reference, **When** a reader looks up any field, **Then** they find:
   - its type;
   - its default;
   - its allowed values;
   - which stage reads it;
   - the rules that check it, with each rule's identifier and meaning.
4. **Given** a validation finding naming a rule (for example `CF-16`), **When** the reader searches
   the site for the identifier, **Then** they find the rule's explanation and how to fix what it
   reports.
5. **Given** a command, option, manifest field or rule is added or changed in the code, **When**
   the documentation is not updated with it, **Then** an automated check fails and names what is
   missing.
6. **Given** the site, **When** a reader looks at any page, **Then** it states which Caravan
   version it describes.

---

### User Story 3 - Know what works today and what is planned (Priority: P2)

A reader planning a project sees on one page what Caravan supports now:
- feature types;
- output types;
- templates;
- boards and what has been verified on each;
- Python versions and extras;
- the operators the export can emit.

They also see what is planned for later and what has been decided against. The roadmap is part of
the site.

**Why this priority**: It is the third part of the owner's request ("was sind momentan die
Kompatibilitäten … und was wird in Zukunft gehen"). It prevents a project from starting on a type,
board or stage that does not exist yet.

**Independent Test**: Pick a board and a feature type and decide from the compatibility page alone
whether a project with them is possible today and how far it has been verified.

**Acceptance Scenarios**:

1. **Given** the compatibility page, **When** a reader looks up a board, **Then** they see the
   highest rung reached for it (`estimated`, `emulated` or `measured`), with the date and, for
   `measured`, the physical board. A board never compiled for is shown as such.
2. **Given** a feature type Ludwig has and Caravan does not (for example `text`), **When** the
   reader looks it up, **Then** the page says it is not supported and why.
3. **Given** the roadmap page, **When** a reader looks for a planned stage (for example `analyze`),
   **Then** they find the version it is planned for and its state.
4. **Given** the roadmap is changed in the repository, **When** the site is next published, **Then**
   the site shows the change. The roadmap exists once, not as a copy.

---

### User Story 4 - Start an own project from own data (Priority: P2)

The owner wants to carry out one or two small projects of their own, end to end onto the board. The
site explains how to get from a CSV of one's own to a manifest:
- choosing each column's type;
- the window;
- the split;
- the template;
- the budgets;
- the boards.

It then leads into the board guide for the last step.

**Why this priority**: It is what turns the example into the owner's own work. It depends on
Stories 1 and 2 and is the test that they are sufficient.

**Independent Test**: With a small CSV that is not the fixture, write a valid manifest using only
the site, and run it through export.

**Acceptance Scenarios**:

1. **Given** a CSV with numeric, categorical and yes/no columns, **When** the author follows the
   own-project guide, **Then** they reach a manifest that validates. The guide explains each choice
   it asks for.
2. **Given** an own model exported for `esp32`, **When** the author follows the board guide with it
   instead of the example, **Then** the only things they change are stated in the guide: the
   model's files and the test windows.
3. **Given** the owner's own project hits a defect of Caravan, **When** it is reported, **Then** it
   is fixed before rc3 or recorded on the compatibility page as a known limit.

---

### Edge Cases

- **Board revision unknown.** The guide tells the author how to recognise the revision and gives
  the OLED pins for each common LoRa32 revision. One setting changes them.
- **The model does not fit the board.** `caravan build` already stops before training (fit check).
  The guide says so, and says what to change.
- **Too small an arena.** The runtime fails to initialise. The board reports this on the serial
  port and the OLED rather than hanging, and the guide says what to do.
- **The runtime library on the board lacks an operator the export's resolver names.** The firmware
  fails to build. The automated build check catches this before a release rather than on the
  author's desk.
- **The board's kernels round differently from the host's.** The decisions are compared, not only
  the raw scores. A score that differs by one quantization step is shown as such, not hidden and
  not counted as a failure. A different decision is a failure.
- **Too many test windows for the board's flash.** The number shipped to the board is bounded and
  stated, and the guide says how to change it.
- **Training needs Python 3.13.** The guide states the Python version for each step: training and
  conversion on 3.13, the rest on any supported version.
- **USB serial driver or port permissions.** The guide names the USB-serial chip of the LoRa32 and
  the usual fixes per operating system.
- **The site is read for a version other than the one installed.** Every page states the version it
  describes.

## Requirements *(mandatory)*

### Functional Requirements

**The board guide (Story 1)**

- **FR-001**: The documentation MUST contain a guide from an empty directory to the example model
  running on a LILYGO LoRa32. The guide's sequence of steps MUST be verified as written.
  - Host steps: install, train, quantize, export.
  - Board steps: the firmware project, build, flash, read the results.
- **FR-002**: The firmware of the guide MUST run every shipped test window through the exported
  model.
  - It MUST show, per window, the decision, the expected class and whether the decision equals the
    host reference's decision.
  - It MUST show a summary of agreements out of windows run.
  - The output MUST go to the OLED and the serial port.
- **FR-003**: The author MUST be able to obtain the test windows in a form the firmware includes
  directly, without writing code and without adding a command verb (Principle XII).
  - The windows come from the test part, as raw values with their expected class and the host
    reference's int8 decision and scores.
  - The number of windows MUST be bounded and stated.
- **FR-004**: The host reference MUST be the quantized model as the pipeline measured it, run on the
  host. It MUST NOT be the float model.
- **FR-005**: The firmware MUST report the arena the runtime actually used, obtained from the
  runtime and not recomputed. It MUST be labeled `measured` with the board named (Principle IV).
  The guide MUST show how to size the arena from it.
- **FR-006**: The firmware MUST report no latency, throughput or energy figure. Those belong to the
  benchmark stage, which follows a public protocol (constitution, verification ladder).
- **FR-007**: The guide MUST cover the common LoRa32 revisions:
  - their OLED pins, settable in one place;
  - how to tell the revisions apart.
- **FR-008**: Every defect the board run finds in what Caravan exports MUST be fixed in Caravan, not
  worked around in the guide. This includes the runner skeleton, the resolver, the headers and the
  interface contract.
- **FR-009**: The guide's firmware project MUST be built for the ESP32 automatically before every
  release. A build failure MUST block the release. It MUST NOT run on changes that touch only
  documentation (Resources & Cost Discipline).
- **FR-010**: The firmware MUST contain no credentials, keys or radio settings. The guide uses
  neither the LoRa radio nor Wi-Fi.

**The documentation site (Stories 2 to 4)**

- **FR-011**: The documentation MUST be published as a website from the repository's `docs/`
  directory on GitHub Pages. The landing page MUST link the CLI reference, the manifest reference,
  the compatibility page, the roadmap, the try-it guide, the board guide and the own-project guide.
- **FR-012**: The landing page MUST say what Caravan is and what it is deliberately not (Principle
  II), show the install, and show the pipeline at a glance.
- **FR-013**: The CLI reference MUST describe every command:
  - its purpose;
  - every argument and option;
  - what it reads and writes;
  - its exit codes.
- **FR-014**: The manifest reference MUST describe every field of `caravan/v0.2`:
  - its type, default and allowed values;
  - which stage reads it;
  - the rules that check it.

  It MUST list every rule identifier with its meaning and how to fix what it reports, including the
  retired ones, marked as retired.
- **FR-015**: An automated check MUST fail when a command, option, manifest field or rule
  identifier exists in the code and is missing from the reference. It MUST name what is missing.
  The check runs with the test suite.
- **FR-016**: The compatibility page MUST state what works today:
  - input and output feature types, with Ludwig's types that are absent and why;
  - templates;
  - boards, with the highest verification rung reached, its date and, for `measured`, the physical
    board;
  - Python versions per extra;
  - the operators the export can emit.

  Each claim MUST rest on a test, a run report or the recorded board run, and never on intention.
- **FR-017**: The roadmap MUST appear on the site from its single source, `docs/roadmap.md`, not as a
  copy. The roadmap MUST be updated to record this feature and the rc3 goal.
- **FR-018**: The own-project guide MUST lead from a CSV of the author's own to a manifest:
  - choosing types, window, split, template, budgets and boards;
  - each choice explained.

  It MUST end in the board guide.
- **FR-019**: Every page MUST state the Caravan version it describes. The published site MUST
  describe the most recent release, so that it matches what a reader installs.
- **FR-020**: Building the site MUST fail on a broken internal link or a page left out of the
  navigation.
- **FR-021**: Publishing the site MUST NOT add a runtime dependency or an extra (Principle XII). The
  site MUST NOT be published on changes that touch only documentation without a release, unless the
  owner triggers it by hand (Resources & Cost Discipline).
- **FR-022**: The existing documents MUST be folded into the site rather than duplicated:
  `docs/try-it.md`, `docs/manifest-changes.md` and `docs/budgets.md`. The try-it guide MUST remain
  executable by the release workflow as it is today.
- **FR-023**: The documentation MUST be in English, as the rest of the repository.

### Key Entities

- **Documentation site**: the published pages. It has a landing page, references, guides, the
  compatibility page and the roadmap. It is versioned to the release it describes.
- **CLI reference**: one entry per command, with arguments, options, inputs, outputs and exit
  codes.
- **Manifest reference**: one entry per field and one per rule identifier.
- **Compatibility record**: what is supported and how far each claim has been verified, with
  provenance.
- **Board guide firmware**: a firmware project for the LoRa32 that includes the exported model, its
  headers and the test windows, and shows results on the OLED and the serial port.
- **Test windows**: a bounded set of windows from the test part, as raw values, with the expected
  class and the host reference's int8 decision and scores.
- **Board run record**: the date, board revision, firmware and toolchain versions, agreement count
  and measured arena of a run on the physical board. It is what the compatibility page cites.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The owner gets the example model running on their LoRa32, with results on the OLED.
  - They follow only the board guide, from an empty directory, in one sitting of at most two hours,
    not counting the toolchain's first download.
- **SC-002**: On the board, every shipped test window gives the same decision as the host reference
  (100%). Every raw score that differs is shown, and none differs by more than one quantization
  step.
- **SC-003**: The automated check finds zero commands, options, manifest fields or rule identifiers
  missing from the references.
- **SC-004**: The site builds with zero broken internal links and zero pages outside the navigation.
- **SC-005**: Each of the five main sections is at most one click from the landing page:
  - the CLI reference;
  - the manifest reference;
  - compatibility;
  - the roadmap;
  - the board guide.
- **SC-006**: The guide's firmware builds for the ESP32 in the automated check before the rc3
  release, with no manual step.
- **SC-007**: The owner completes at least one project of their own (own data, own manifest) onto
  the board using only the site. Every Caravan defect it finds is fixed or recorded as a known limit
  before rc3.
- **SC-008**: The compatibility page shows `esp32` as `measured` on a LoRa32 with the date of the
  owner's run. No board is shown at a rung it has not reached.

## Constitution

The principles this feature touches, and how it complies:

- **II (Embedded targets only)**: the landing page states the scope and the non-goals. The guide
  ends on a microcontroller.
- **III (Reproducible)**:
  - the guide pins the Caravan version, the toolchain and the runtime library it was verified with;
  - the firmware build check uses the same pins.
- **IV (Always labeled)**:
  - the measured arena carries `measured` with the board;
  - the compatibility page labels every board claim by rung;
  - no timing figure is shown (FR-006).
- **VI (The data is the author's)**: the guide uses the synthetic fixture only. An own project's
  windows come from the author's own data and stay out of the repository.
- **VIII (No lock-in)**: the firmware uses the vendor's open runtime component and an open build
  tool. The exported files are the same for any toolchain.
- **XI (No Claude in model learning)**: unaffected. No model is trained, labeled or evaluated by
  Claude. Documentation is not model learning.
- **XII (Small core)**:
  - no command verb is added (FR-003);
  - no runtime dependency or extra is added (FR-021);
  - the site's build tool is a documentation tool, outside the installed package.
- **Target Hardware & the Verification Ladder**: the ESP32 has no emulated rung, so the physical
  board is the next rung. Its result is recorded as a board run. The automated build check proves
  the firmware builds, not how it behaves.
- **Resources & Cost Discipline**:
  - documentation-only changes trigger no CI and no publication;
  - the firmware build runs before releases, not on every change;
  - the board is already owned. No cash cost, so no cash budget is needed.
- **Datasets and credentials**: none in the repository or the firmware (FR-010).

## Assumptions

- The board is a LILYGO LoRa32 (ESP32, 4 MB flash, an SSD1306-class OLED on I2C), matching the
  `esp32` board description. Its revision is unknown, so the guide covers the common ones (FR-007).
- The build and flash tool is PlatformIO, the owner's choice of 2026-10-26. It uses Espressif's
  TensorFlow Lite Micro component with the ESP-NN kernels the board description names.
- The example is the existing `picket-mlp` manifest on the synthetic fixture. No dataset enters the
  repository.
- The owner performs the physical board run. The automated check can only prove that the firmware
  builds, because the ESP32 has no emulator in the ladder.
- The site describes the latest release. It is published when a release is made and on demand.
  Documentation between releases waits for the next one or a manual publish.
- The site uses the repository's public GitHub Pages. The repository is public under Apache-2.0.
- Reaching rc3 is a release decision the owner makes. This feature delivers what rc3 is meant to
  contain; tagging it needs the owner's go-ahead.
- Real sensor input on the board is out of scope. The guide shows where an own firmware would pass
  live raw values: the generated fill functions of the interface contract.
- Out of scope:
  - the LoRa radio, Wi-Fi and any networking;
  - latency and energy figures;
  - boards other than the LoRa32;
  - the Arduino IDE and plain ESP-IDF routes;
  - a translated site.
