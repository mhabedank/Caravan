# Feature Specification: Documentation organised like Django's

**Feature Branch**: `012-docs-restructure`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: Restructure Caravan's documentation the way Django's documentation is organised. A visitor immediately sees what Caravan is — machine learning for microcontrollers and sensors, embedded and IoT — and learns in the shortest time how to use it, above all the CLI and the manifest. The model is Django's documentation: an overview page with "First steps" (a "From scratch" row and the tutorial), "Getting help", "How the documentation is organized", and one section per layer with a one-line definition and grouped links; four documentation types; links to important concepts throughout the running text; a glossary; reference objects linked from running text the way Django links `django.db.models.Model`; reusable page components. Decided by the owner: the manifest reference is split into sub-pages; this is its own feature after 011; the pages are product pages in plain language, with no hedging.

## Why this feature exists

Feature 011 fixed the first screen: the landing page now says what Caravan is and shows a manifest
beside the model it builds. Behind that screen the documentation is still a list of twenty pages
in four loose groups. A reader who wants to know how `export.targets` works has to know that it
lives on a 900-line page under "Reference"; a reader who meets the word "gate" in the tutorial has no way
to find out what it means without leaving the page and searching.

Django's documentation is the owner's model because it solves exactly this. One overview page says
what kinds of documentation exist and where each layer of the framework is explained. Every
concept in running text is a link. Every class has one canonical place, and every mention of it
anywhere points there. A newcomer follows the tutorial; someone who already knows what they want
goes to the layer and the reference in two clicks.

This feature gives Caravan the same shape. It does not rewrite what the pages say about Caravan;
it gives what they say a structure a reader can navigate, and links that make the structure
usable.

## Clarifications

### Session 2026-10-29

- Q: Which links should the header of every page carry once the documentation overview exists? →
  A: Only "Documentation" and "Search", as in Django's documentation; everything else is reached
  through the overview (FR-001, SC-001).
- Q: When a page changes type, should its web address change to match, or stay as it is? → A: Every
  page gets an address that names its type, as Django's do — `intro/`, `topics/`, `ref/`, `howto/`
  — the tutorial included. And the route-and-legs metaphor goes: the tutorial is called a tutorial
  and its four legs are four parts, everywhere on the site (FR-006, FR-021, FR-024).
- Q: What should happen to the three long sections at the bottom of the landing page? → A: Their
  content moves — "What it actually does" and "What Caravan is for" into "Caravan at a glance",
  "What you bring" into "Installation" — and the landing page ends after the tutorial cards
  (FR-025).

## User Scenarios & Testing *(mandatory)*

The reader is an embedded developer: someone with a microcontroller, sensor data and no wish to
learn a machine-learning framework. The second reader is the owner, who maintains these pages.

### User Story 1 - Find the way in from one page (Priority: P1)

A reader who has decided Caravan might be useful opens the documentation overview from the site's
header. One page tells them where to start if they are new, where to get help, how the
documentation is organised, and — for each layer of Caravan — what that layer is, in one sentence,
with links to its tutorial, topic guides, reference and how-to guides.

**Why this priority**: it is the page every other page hangs from. Without it the rest of this
feature is twenty pages with better links and no map.

**Independent Test**: from the landing page, open the overview and, for each layer, reach its
reference page in one click. Show the overview to someone who has not seen Caravan and ask where
they would go to start, to look up a manifest field, and to look up a CLI command.

**Acceptance Scenarios**:

1. **Given** any page of the site, **When** the reader uses the header, **Then** one link opens the
   documentation overview, and the only other entry is search.
2. **Given** the overview, **When** the reader reads it top to bottom, **Then** it shows, in this
   order: First steps (a "From scratch" row and the tutorial), Getting help, How the documentation
   is organized, then one section per layer with a one-sentence definition and links grouped by
   documentation type.
3. **Given** the overview, **When** the reader wants the manifest reference or the CLI reference,
   **Then** each is one click away.

---

### User Story 2 - Look up one manifest field fast (Priority: P1)

A reader writing a manifest wants to know what `preprocessing.window_size` does, its default, and
what to change it to. They open the manifest reference and land on a short page for the
`preprocessing` section, where the field has its own entry with its type, its default, what it
does and when to change it.

**Why this priority**: the manifest is what a reader writes. The current single page is the longest
on the site and the slowest place to find one field.

**Independent Test**: for a sample of ten fields, start at the overview and reach the field's entry
in two clicks, or one search.

**Acceptance Scenarios**:

1. **Given** the manifest reference, **When** the reader opens it, **Then** they see a short overview
   with a first manifest and links to one sub-page per section of the manifest.
2. **Given** a sub-page, **When** the reader scans it, **Then** every field of that section has its
   own entry with its full name, type, default and description.
3. **Given** a link to a field on the old single page, **When** someone follows it, **Then** it
   reaches that field's entry on its new sub-page.

---

### User Story 3 - Every name in the text is a link (Priority: P1)

A reader in part 2 of the tutorial reads that `export.targets` decides which boards the model has to
fit and that `caravan export` will refuse a model that does not. Both names are links: one to the
field's entry, one to the command's entry. The word "gate" is a link to the glossary.

**Why this priority**: this is what the owner admires most in Django's documentation, and it is
what turns a set of pages into one piece of documentation.

**Independent Test**: on any tutorial or topic page, every manifest field, CLI command, validation
rule and board named in running text is a link to its entry, and the first use of each glossary
term in a section is a link to the glossary.

**Acceptance Scenarios**:

1. **Given** running text that names a manifest field, a CLI command, a validation rule or a board,
   **When** the page is built, **Then** the name links to that object's single entry.
2. **Given** a name that does not resolve to an entry, **When** the site is built, **Then** the build
   fails and names the page and the name.
3. **Given** the glossary, **When** the reader opens it, **Then** each term has a definition of one
   or two sentences, and where a topic guide explains it further, a link to that guide.

---

### User Story 4 - Learn the pieces from scratch (Priority: P2)

A reader who has never trained a model wants the whole picture before the tutorial. "Caravan at a
glance" walks one example manifest through every stage to the C files on one page; "Installation"
gets Caravan installed and checked on its own page, so the tutorial starts with work rather than a
download.

**Why this priority**: it is the "From scratch" row of Django's first steps. It is P2 because the
tutorial already works without it.

**Independent Test**: a reader reads "Caravan at a glance" in under ten minutes and can name the
stages a manifest goes through; following "Installation" ends with a check that proves the install
works.

**Acceptance Scenarios**:

1. **Given** "Caravan at a glance", **When** the reader finishes it, **Then** they have seen one
   manifest go through every stage, with a link at each stage to its topic guide and reference,
   and they know what Caravan is for and what it deliberately leaves out.
2. **Given** "Installation", **When** the reader follows it, **Then** it states what they need —
   their own data, the supported Python, the download, the operating systems, a board only from
   part 3 — and ends with one command whose output proves Caravan is installed; part 1 of the
   tutorial links to it instead of repeating it.

---

### User Story 5 - Know what a page will teach, and where to go next (Priority: P2)

A reader opening a tutorial part or a topic guide sees at the top what they will learn, and at the
bottom a link to the previous and the next page in that sequence. Notes, warnings and "see also"
pointers appear as boxes a reader can tell apart from the running text.

**Why this priority**: the components are what make Django's pages scannable. They are P2 because
the structure and the links carry more of the value.

**Independent Test**: every tutorial part and topic guide opens with a "you will learn" box and ends
with previous/next links; each kind of box is visually distinct and legible in the light and the
dark colour scheme.

**Acceptance Scenarios**:

1. **Given** a tutorial part or a topic guide, **When** the reader opens it, **Then** a "you will
   learn" box lists what the page teaches in three to five points.
2. **Given** a page in a sequence, **When** the reader reaches its end, **Then** links to the
   previous and the next page are there, named by their titles.
3. **Given** a note, a warning and a "see also" box, **When** they appear on a page, **Then** each is
   visually distinct from the others and from running text, in both colour schemes.

---

### User Story 6 - Recipes for the two things readers ask most (Priority: P3)

A reader who has finished the tutorial wants to add their own board, or to choose a budget for
their own model. Each is a short how-to guide: a goal, the steps, the result, and links to the
reference for every field and command used.

**Why this priority**: how-to guides are the last of Django's four types and the one that grows on
demand. Two are enough to establish the type.

**Independent Test**: following "Add a board" with a board's datasheet ends with the new board
listed by `caravan boards` and accepted in `export.targets`; following "Choose a budget" ends with a
budget the reader can justify from a run's numbers.

**Acceptance Scenarios**:

1. **Given** "Add a board", **When** the reader follows it, **Then** they end with a board file the
   pipeline accepts, and every field of that file is linked to its reference entry.
2. **Given** "Choose a budget", **When** the reader follows it, **Then** they end with an
   `accuracy_drop_max` chosen from the numbers their own run printed.

---

### Edge Cases

- **A deep link into the old manifest page.** Links like `reference/manifest.html#export-targets`
  exist outside the site. The old page becomes the manifest overview, and a link to a field on it
  must still reach that field on its sub-page.
- **A moved page.** Every page that moves keeps its old address working, and the forward does not
  show up in search or in the navigation.
- **A name that is both a field and a word.** `window` is a glossary term and part of a field name;
  links go to the field when the text means the field, and to the glossary when it means the
  concept.
- **The same term twice in a section.** Only the first use links; a paragraph where every second
  word is a link is unreadable.
- **A heading.** Headings carry no links; the first use after the heading does.
- **Checks that run the tutorial.** The test that runs the tutorial's commands, the release
  workflow that runs part 1 against the published release, and the firmware workflow all name the
  tutorial's files by path; they follow the pages to their new addresses, and still run what the
  pages say.
- **A number about hardware.** It keeps its `estimated`, `emulated` or `measured` label. That label
  is a fact about the number, not a hedge, and the no-hedging rule does not remove it.
- **An object in code with no entry.** A manifest field, CLI command, validation rule or board that
  exists in the code but has no entry is a defect the existing reference checks already catch;
  they must keep catching it after the split.

## Requirements *(mandatory)*

### Functional Requirements

**The overview**

- **FR-001**: The site MUST have a documentation overview page, separate from the landing page. The
  header of every page MUST carry exactly two entries, "Documentation" (the overview) and "Search";
  the tutorial, the topic guides, the references and the project pages are reached through the
  overview.
- **FR-002**: The overview MUST present, in this order: "First steps" with a "From scratch" row
  (Caravan at a glance, Installation) and a tutorial row (its four parts); "Getting help" (the
  glossary, the index of reference objects, what is verified today, where to report a problem);
  "How the documentation is organized" (the four types, one sentence each); then one section per
  layer.
- **FR-003**: The layers MUST be: the manifest; the pipeline and the CLI; boards and targets;
  verification (budgets and gates); the exported model and the firmware; and a closing section
  for the project (roadmap, releases, credits).
- **FR-004**: Each layer section MUST open with a one-sentence definition of the layer and group its
  links under the documentation types it has (tutorial, topic guide, reference, how-to).

**The four documentation types**

- **FR-005**: Every page MUST be exactly one of: tutorial, topic guide, reference guide, how-to guide,
  or a project page; the overview states what each type is for.
- **FR-006**: The four legs of what was the route MUST become the tutorial, in four parts. The four
  concept pages MUST become topic guides. The budget numbers, the manifest changes and the
  compatibility pages MUST move into the reference.
- **FR-007**: The site MUST gain: the overview, "Caravan at a glance", "Installation", a topic guide
  on the pipeline, a glossary, and two how-to guides, "Add a board" and "Choose a budget".

**The manifest reference**

- **FR-008**: The manifest reference MUST be split into a short overview — keeping "A first manifest"
  and "A complete example" — and one sub-page per top-level section of the manifest: the top level,
  `model`, `input_features`, `output_features`, `preprocessing`, `defaults`, `trainer`, `export`.
- **FR-009**: Every manifest field MUST have exactly one entry, under its full dotted name, stating
  its type, its default, what it does and when to change it.
- **FR-010**: A link to an anchor on an old reference page — a field on the single manifest page, a
  command on the CLI page, a rule on the rules page — MUST reach that entry at its new address.

**Linkable reference objects**

- **FR-011**: Every manifest field, CLI command, validation rule and board MUST have one canonical
  entry that any page can link to by its name — the field by its dotted name, the command by
  `caravan <verb>`, the rule by its code, the board by its identifier.
- **FR-012**: Running text on tutorial, topic and how-to pages MUST link every such name it mentions
  to its entry. Code blocks are not linked.
- **FR-013**: The site MUST have an index listing every reference object by kind and name, linked
  from "Getting help".
- **FR-014**: A link to a name that has no entry MUST fail the site build, naming the page and the
  name.

**The glossary**

- **FR-015**: The glossary MUST define at least twenty terms, one or two sentences each, alphabetical,
  each linking to the topic guide that explains it where one exists. It MUST include every
  abbreviation the existing abbreviation check knows.
- **FR-016**: On tutorial, topic and how-to pages, the first use of a glossary term in each section
  MUST link to its definition; later uses in the same section MUST NOT.

**Components**

- **FR-017**: Notes, warnings and "see also" pointers MUST appear as distinct boxes in the site's
  identity, legible in the light and the dark colour scheme.
- **FR-018**: Every tutorial part and topic guide MUST open with a "you will learn" box of three to
  five points.
- **FR-019**: Every page in a sequence — the tutorial parts, the topic guides, the how-to guides —
  MUST end with links to the previous and the next page of that sequence, named by title.
- **FR-020**: Each topic guide MUST end with a "see also" box pointing to the reference entries it
  explains.

**Addresses and language**

- **FR-021**: Every documentation page's address MUST name its type, as Django's do: the
  at-a-glance page, installation, the tutorial and its parts under `intro/`; topic guides under
  `topics/`; reference guides — the manifest sub-pages, the CLI, the rules, the boards, the budget
  numbers, the manifest changes, what is verified today, the board runs — under `ref/`; how-to
  guides under `howto/`. The contents page and the glossary sit at the root, as Django's
  `contents/` and `glossary/` do, and the project pages keep their addresses. Every page whose
  address changes MUST keep its old address working through a forward that is excluded from search
  engines and from the site's own search.
- **FR-022**: The pages are product pages. Running text MUST state what is true plainly and MUST NOT
  relativise it: no cumulative-time arithmetic, no "about", "roughly" or "should" in place of a
  fact, no apologies for what is not done. A limit a reader needs is stated once, as a fact, where
  it applies.
- **FR-023**: No statement may claim more than is verified; the provenance labels of numbers about
  hardware stay (Principle IV).
- **FR-024**: No page, heading, label, button or address MAY use the route-and-legs metaphor. The
  landing page's "Start the route" and "The route" become the tutorial, its cards are labelled as
  parts, and the tutorial's own pages are titled as parts of a tutorial. The README and the example
  manifests use the same names. Two things are not pages and keep their names: the forwards at the
  old `route/` addresses, which no reader reads, and the image identifiers recorded in each image's
  provenance record and in the credits, which renaming would rewrite.
- **FR-025**: The landing page MUST end after the tutorial cards. The content of its sections "What
  it actually does" and "What Caravan is for" MUST move into "Caravan at a glance", and "What you
  bring" into "Installation"; nothing they state is dropped, only the hedging (FR-022).

**Constraints**

- **FR-026**: The restructure MUST add no dependency, extra or dependency group to the distribution.
- **FR-027**: The site build MUST keep failing on any warning, and the existing documentation checks
  MUST stay green, adapted where pages move. No new test suite is added: unresolved links are
  caught by the build (FR-014), not by new tests.
- **FR-028**: The documentation CI job MUST stay inside the ten minutes the constitution bounds it to.

### Key Entities

- **Page**: one page of the site. Has a type (tutorial, topic guide, reference guide, how-to guide,
  project page), a layer, and — if it is in a sequence — a previous and a next page.
- **Reference object**: a manifest field, a CLI command, a validation rule or a board. Has a kind, a
  canonical name and exactly one entry; appears in the index.
- **Glossary term**: a word with a one- or two-sentence definition and, where one exists, a link to
  the topic guide that explains it.
- **Forward**: an old address and the new address it leads to, including the field anchors of the
  old manifest page.
- **Box**: a note, warning, "see also" or "you will learn" box.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From any page, the documentation overview is one click away and the reference of
  every layer two; from the landing page, the CLI and manifest references are one click away
  through its own buttons.
- **SC-002**: For ten sampled manifest fields, a reader reaches the field's entry from the overview in
  at most two clicks.
- **SC-003**: Every manifest field, CLI command, validation rule and board in the code has exactly one
  entry, and every link to one resolves — the build fails otherwise. That running text writes each
  mention as a link (FR-012) is checked in review, not by the build.
- **SC-004**: The glossary has at least twenty terms, and on every tutorial, topic and how-to page the
  first use of a term in a section links to it.
- **SC-005**: Every address the site had before this feature still answers, including links to
  fields on the old manifest page.
- **SC-006**: Every tutorial part and topic guide has a "you will learn" box and previous/next links.
- **SC-007**: Shown the overview for two minutes, four of five people who do not know Caravan can say
  what it does and where they would look up a manifest field and a CLI command.
- **SC-008**: The documentation CI job stays under ten minutes, and the number of test files does not
  grow.

## Principles this touches

- **IV. Measured, Emulated or Estimated**: numbers about hardware keep their labels through every
  rewrite (FR-023). Plain language removes hedging, not provenance.
- **XII. Small Core, Few Dependencies**: nothing is added to the distribution (FR-026). Whatever the
  linking needs is built from what the site's build tools already provide.
- **Resources & Cost Discipline**: the documentation job stays one job inside ten minutes (FR-028),
  and the owner's earlier decision that the site gets checks, not a test suite, stands (FR-027).
- **Development Workflow & Quality Gates**: this spec lists the principles it touches; the plan will
  check them before and after design.

## Assumptions

- The site keeps its build tools — Sphinx 9.2 with MyST, pinned in the documentation dependency
  group — and its theme and identity from feature 010 and the landing page from feature 011.
- "Getting help" links to the project's issue tracker as the place to report a problem; there is no
  forum or chat.
- The tutorial keeps the content of the four legs of what was called the route, as four parts;
  "From scratch" means the two new pages before it, not a fifth part.
- Every reference page moves under `ref/` (FR-021), the manifest reference included; its old
  address `reference/manifest.html` becomes a forward. Links to a field, a command or a rule on the
  old pages keep reaching it on the new ones: the old anchors are a recorded fact (54 on the
  manifest page, 12 on the CLI page, 62 on the rules page, from the build of feature 011), and each
  is forwarded to its entry (FR-010).
- How-to guides beyond the first two are written when readers ask for them.
- The documentation is in English only and describes the current release only.

## Out of scope

- Rewriting what each reference entry says. Entries are moved, split and linked; their content
  changes only where the no-hedging rule (FR-022) or a broken claim (FR-023) requires it, or where
  an entry lacks a part FR-009 requires — its type, its default, or when to change it.
- Documentation for several versions at once, and translations.
- A reference for Caravan's Python internals: Caravan is used through its CLI and its manifest.
- A new visual identity. Boxes and navigation use the existing identity.
- New generated images; the imagery of feature 011 stays as it is.
