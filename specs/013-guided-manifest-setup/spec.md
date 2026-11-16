# Feature Specification: A Guided Way to Write the Manifest

**Feature Branch**: `013-guided-manifest-setup`

**Created**: 2026-11-16

**Status**: Draft

**Input**: User description: "die yaml selber zu schreiben ist nervig und umständlich. ich denke es
sollte ein CLI oder TUI tool geben, dass einen durch die konfiguration führt" — *Writing the YAML
by hand is tedious and awkward. There should be a CLI or TUI tool that walks you through the
configuration.*

## Context

Today an author starts by writing a manifest by hand: copy an example, read the reference, and
then guess at column names, feature types, a template, the boards and the budgets. The reference
documents every field, but a new author has to know *which* fields their model needs before the
reference helps, and the first `validate` run is often the first time they learn what is missing.

Much of what the author types is already known to Caravan, or can be read from what they already
have:

- the column names are in the header of their data;
- a sensible type for each column can be proposed from its values (a column of two values is
  likely `binary`, a column of a few repeated codes is likely `category`, a column of varying
  numbers is likely `number`);
- the templates, the boards and which output type each template serves are registered;
- the defaults come from the template and the board description (Principle I).

What Caravan cannot know is the author's intent: which column is the answer, which columns the
model may read, how much accuracy they will give up for int8, and which boards they have. The
guided setup asks for exactly that, proposes everything else, and writes a manifest that validates.

The result is the same manifest an author would have written by hand. The guided setup does not
replace the manifest or become a second way to describe a model; it is a way to get to the first
one faster.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - From a data directory to a manifest that validates (Priority: P1)

An author has a directory of CSV files and a board. They start the guided setup, point it at the
data, and answer a short series of questions. Each question shows the choices Caravan offers and
the one it proposes. At the end a manifest file is written, and it passes `caravan validate`
without a single edit.

**Why this priority**: This is the owner's complaint as stated: writing the YAML by hand is the
obstacle. A first valid manifest is the whole value; everything else builds on it.

**Independent Test**: In an empty directory beside the synthetic dataset, run the guided setup,
accept every proposal and name `label` as the output. Run `caravan validate` on the written file:
it exits 0. Run `caravan render` on it: every input and output appears with its resolved settings.

**Acceptance Scenarios**:

1. **Given** a directory of CSV files with a header row, **When** the author names it as the data,
   **Then** the setup lists every column with a proposed type and the reason for the proposal (for
   example "4 distinct values in 5,184 rows").
2. **Given** the listed columns, **When** the author picks the column the model answers, **Then**
   that column is offered only the output types that fit its values, and is removed from the
   inputs.
3. **Given** the chosen output type, **When** the setup offers templates, **Then** it offers only
   templates that serve that output type and those inputs, and says what each one is for in one
   line.
4. **Given** the registered boards, **When** the author picks one or more, **Then** each choice
   shows the board's memory and flash so the author knows what they are choosing.
5. **Given** an output that needs a quality budget (`accuracy_drop_max` for `category` and
   `binary`, `auc_drop_max` for `anomaly`), **When** the setup reaches it, **Then** it asks for the
   value, explains in one sentence what it gates, and offers the value the examples use as the
   proposal.
6. **Given** all answers, **When** the setup finishes, **Then** it writes the manifest, runs the
   same validation as `caravan validate` on it, and reports the result and the next command to
   run.

---

### User Story 2 - A manifest the author can read and change by hand afterwards (Priority: P2)

The written file is meant to be kept, put under version control and edited later. It contains only
what the author chose or what the schema requires, so it stays short; a comment at each section says
in one line what the section is for and where its defaults come from.

**Why this priority**: Principle I makes the manifest the model's description. A generated file
that is long, opaque or full of defaults copied out of the template becomes the thing nobody wants
to edit, which is the problem this feature exists to solve.

**Independent Test**: Generate a manifest by accepting every proposal. Compare it with the
minimal form the reference describes: it carries no field whose value equals the template's or the
board's default, and every section has a one-line comment. Change one value by hand and validate
again: it still validates.

**Acceptance Scenarios**:

1. **Given** the author accepted a template default, **When** the manifest is written, **Then** the
   default is not written into the file, and `render` shows it as resolved from the template.
2. **Given** the author changed a value from its default, **When** the manifest is written, **Then**
   the changed value is in the file.
3. **Given** a written manifest, **When** it is opened in an editor, **Then** each section starts
   with a one-line comment, and the header comment names the data it was set up from and points to
   the manifest reference.
4. **Given** columns the author did not select, **When** the manifest is written, **Then** a
   comment lists them as ignored, so the choice is visible in the file and not only in the session.

---

### User Story 3 - The same setup without questions, for scripts and tests (Priority: P3)

An author or a test suite gives every answer up front — data, output column, template, boards,
budgets — and the setup writes the manifest without asking anything. Where an answer is missing and
there is no proposal it can take, it stops and names what is missing rather than guessing.

**Why this priority**: It makes the guided setup testable end to end in continuous integration and
usable in a project's own scripts. It is not what the owner asked for, so it comes last.

**Independent Test**: Run the setup with every answer given and no terminal attached. The written
manifest is byte-identical to the one an interactive session with the same answers writes, and it
validates.

**Acceptance Scenarios**:

1. **Given** every required answer, **When** the setup runs without a terminal, **Then** it writes
   the manifest and asks nothing.
2. **Given** no output column, **When** the setup runs without a terminal, **Then** it exits with
   the usage error code and names the missing answer and how to give it.
3. **Given** the same answers twice, **When** the setup runs twice, **Then** both files are
   byte-identical.

---

### Edge Cases

- **A manifest already exists at the target path**: the setup never overwrites it silently. It asks
  for a different name or an explicit confirmation; without a terminal it refuses unless told to
  overwrite.
- **The data directory is missing, empty, or has files without a header row**: the setup says which
  path and what is wrong, before asking anything else.
- **The files of the directory have different headers**: the setup says which files differ and in
  which columns, and stops; it does not pick one.
- **A column has missing values**: the proposal says so, and the type is proposed from the values
  present.
- **A column has a single value in every row**: it is proposed as ignored, with the reason, because
  it carries no information.
- **No template serves the chosen output and inputs**: the setup says so and names what would make
  one fit (for example "`anomaly` needs the `autoencoder` template"), rather than offering a choice
  that will fail validation.
- **The author aborts mid-way** (interrupt, end of input): nothing is written, and the setup exits
  without a traceback.
- **The terminal is narrow or does not support colour or cursor movement**: the setup still works
  and is still readable.
- **A very large dataset**: proposing types reads a bounded sample, says that it did, and does not
  make the author wait more than a few seconds.
- **The image input**: a directory of image files rather than CSV columns is out of this feature's
  first version (see Assumptions); the setup says so and points to the manifest reference for
  `image` inputs, rather than failing obscurely.

## Requirements *(mandatory)*

### Functional Requirements

**Starting and finishing**

- **FR-001**: Caravan MUST offer a guided setup that, from a data directory and the author's
  answers, writes one manifest file.
- **FR-002**: The guided setup MUST be started through [NEEDS CLARIFICATION: Principle XII fixes
  the set of command-line verbs and requires an amendment to add one. Is the guided setup a new
  verb (`caravan init`, with a constitution amendment), or does it live elsewhere?].
- **FR-003**: The written manifest MUST pass the same validation as `caravan validate`, and the
  setup MUST run that validation itself before it reports success.
- **FR-004**: The setup MUST NOT overwrite an existing file without the author's explicit
  confirmation, and MUST write nothing when it is aborted.
- **FR-005**: The setup MUST end by stating the path written, the validation result and the next
  command to run.
- **FR-006**: The setup MUST follow Caravan's exit codes: 0 when the manifest was written and
  validates, 1 when a rule says no, 2 on a usage error, 3 on a defect in the tool itself.

**What it asks and what it proposes**

- **FR-007**: The setup MUST ask only for what a stage reads (Principles I and VI). It MUST NOT
  ask for descriptions, units, licences or any other information no stage uses.
- **FR-008**: The setup MUST read the column names from the data and MUST propose a type for each
  column from its values, showing the reason for each proposal. The author MUST be able to accept
  or change every proposal.
- **FR-009**: The setup MUST ask which column or columns the model answers, and MUST offer each
  output only the output types its values allow.
- **FR-010**: The setup MUST offer only templates that serve the chosen inputs and outputs, and
  only registered boards. It MUST obtain both lists from the registries, so that a template or
  board added later appears without changing the setup (Principle VII).
- **FR-011**: The setup MUST ask for every budget the schema requires for the chosen outputs and
  boards, explain what each budget gates, and MUST NOT write a budget the author did not confirm.
- **FR-012**: Every question MUST show its proposal, and accepting the proposal MUST take a single
  keystroke.
- **FR-013**: The setup MUST let the author go back to the previous question without starting over.
- **FR-014**: The setup MUST show a summary of all answers before it writes, and the author MUST be
  able to confirm or go back.
- **FR-015**: Labels and other values that follow from the data MUST NOT be asked for (Principle
  I); the setup MAY show them as derived.

**What it writes**

- **FR-016**: The manifest MUST declare the schema version the installed Caravan implements.
- **FR-017**: The manifest MUST NOT contain a field whose value equals the default resolved from the
  template or the board description, unless the schema requires it.
- **FR-018**: The manifest MUST carry a one-line comment per section, a header comment naming the
  data it was set up from, and a comment listing the columns left out.
- **FR-019**: The data path in the manifest MUST be written relative to the manifest's own
  location, so the pair can be moved together.
- **FR-020**: Given the same answers and the same data, the setup MUST write a byte-identical file.

**How it runs**

- **FR-021**: The setup MUST be usable without questions, with every answer given up front; a
  missing answer without a proposal MUST be a usage error naming the answer and how to give it.
- **FR-022**: The setup MUST work in a plain terminal without colour or cursor control, and when its
  input is not a terminal.
- **FR-023**: The setup MUST run in the default installation, without the training or verification
  extras, on every supported Python version, and MUST NOT require network access (Principles VIII
  and XII).
- **FR-024**: The setup MUST NOT add a runtime dependency to the default installation beyond the
  budget of Principle XII, and any dependency it adds MUST be isolated behind one module.
- **FR-025**: The interaction style MUST be [NEEDS CLARIFICATION: line-by-line questions in the
  terminal (a CLI dialogue), or a full-screen interface with lists, panes and keyboard navigation (a
  TUI)?].

**Scope**

- **FR-026**: The setup MUST [NEEDS CLARIFICATION: only create new manifests, or also open an
  existing manifest and change it (add a column, change a board) while keeping the author's
  comments and layout?].

### Key Entities

- **Guided session**: one run of the setup, from the data path to a written file. It holds the
  answers so far, the proposals and the position for going back.
- **Column profile**: what the setup observed of one column in the sample: its name, the count of
  distinct and missing values, whether every value is numeric, and the type proposed with its
  reason. It is shown to the author and not written to the manifest.
- **Answer set**: the complete set of choices the manifest is written from — data path, inputs with
  types, outputs with types and budgets, template, boards. It is the same whether answered
  interactively or given up front.
- **Written manifest**: the output, an ordinary manifest file indistinguishable in kind from one
  written by hand.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An author who has never written a Caravan manifest goes from a data directory to a
  manifest that validates in under 5 minutes, without opening the documentation.
- **SC-002**: 100% of manifests the setup writes pass `caravan validate` unchanged, across every
  combination of registered template, output type and board the setup offers.
- **SC-003**: Accepting every proposal on the synthetic dataset, with `label` as the output, takes
  no more than 12 answers.
- **SC-004**: A manifest written by accepting every proposal is no longer than the hand-written
  example for the same data (`examples/picket-mlp.yaml`), counted in lines of fields excluding
  comments.
- **SC-005**: Proposing types for a dataset of one million rows takes under 5 seconds.
- **SC-006**: Adding a board description or a template makes it appear in the setup's choices with
  zero changes to the setup.
- **SC-007**: The owner, writing the manifest for their next model, chooses the guided setup over
  copying an example.

## Assumptions

- **The data is tabular**: the first version reads directories of `.csv`, `.tsv` and `.txt` files
  with a header row, the form `dataset` accepts today. Directories of images for the `image` input
  are a later step; the setup recognises them and says so.
- **One model per run**: one session writes one manifest (Principle I).
- **Preprocessing, trainer and export options** beyond what the schema requires are left at their
  defaults and not asked for. The window size and the split are asked for only where the chosen
  template has no default for them. An author who wants to change a default edits the file, and the
  header comment says where the reference is.
- **Proposals are proposals**: the type proposed for a column is a heuristic and is labelled as such.
  A CAN identifier that looks like a number but is a code is exactly the case the author is asked
  to confirm (feature 008).
- **Budget proposals** come from the values the shipped examples use and are labelled as such;
  they are not a recommendation for the author's model.
- **English only**: the questions are in English, like the rest of Caravan's output.
- **Before 1.0.0** (Principle IX), the setup writes the current schema version only and does not
  need to produce manifests for earlier versions.
- **Dependency on governance**: if the answer to FR-002 is a new verb, a constitution amendment to
  Principle XII is required before the feature is released, and the roadmap gains the item.
