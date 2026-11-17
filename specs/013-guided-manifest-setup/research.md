# Research: A Guided Way to Write the Manifest

**Feature**: 013-guided-manifest-setup · **Date**: 2026-11-16

Each entry: what was decided, why, and what was weighed instead. Facts about the code were read from
the repository at commit `9840d3e`; facts about the fixtures were measured on the files in
`tests/fixtures/datasets/`.

---

## R1. How the dialogue is driven: the standard library, no new dependency

**Decision**: The dialogue uses `input()`-style line reading on standard input and writes its
questions to standard error. No prompt or terminal library is added. Colour and cursor control are
not used at all in this feature.

**Rationale**: FR-025 and the amendment of Principle XII (v4.3.0) require the line-by-line form with
no runtime dependency; the default installation has two of its six allowed (`pydantic`,
`ruamel.yaml`). Reading lines also makes the dialogue scriptable for free: a test pipes the answers
in, one per line, and the same code path runs (R6). Questions go to standard error because the CLI
contract keeps standard output for an answer a program reads (`test_cli_contract.py`), and `init`'s
only such answer is the path it wrote.

**Alternatives considered**:
- *A prompt library (questionary, prompt_toolkit, InquirerPy)*: arrow-key lists and completion, at
  the cost of a dependency and a terminal requirement. Deferred to the later full-screen extra the
  owner named; the questions and the answer set (data-model.md) are designed so that extra can drive
  the same session object.
- *`readline` for line editing*: not available on every platform's Python, and line editing is not
  what makes the dialogue hard to use. Not needed.

---

## R2. Reading the data without the training extra

**Decision**: Column profiling reads the tables with the standard library's `csv` module, in a new
core module that imports nothing outside the standard library and `caravan.data.fingerprint`. It
lists files through a public helper split out of `fingerprint._files_in`, and never calls
`resolve_dataset`, which hashes every byte.

**Rationale**: `caravan.data.reader` is the only module that parses a dataset today, and it imports
`numpy`, which sits behind the `train` extra (its docstring and Principle XII's layering rule). FR-023
requires `init` in the default installation on every supported Python, including 3.15 where the
extra installs no framework. `fingerprint.py` already reads headers with `csv` under the same
constraint, so the pattern exists. Hashing is not needed to propose a type and would make SC-005 depend
on the dataset's size.

**Alternatives considered**:
- *Reuse `caravan.data.reader`*: drags `numpy` into `init`; fails on a default installation.
- *Move header checks out of the reader into a shared core module*: a larger refactor than this
  feature needs. The profiler reports a header mismatch in its own words (edge case "files have
  different headers"), naming the files and the columns, as the reader's DS rule does at run time.

---

## R3. How much of the data is read

**Decision**: The profiler reads rows in file order until it has read 50,000 data rows or reached
the end of the data, and says which it did ("sampled the first 50,000 rows" or "read all 5,184
rows"). Per column it keeps: the count of rows seen, the count of empty cells, whether every
non-empty cell parses as a number, whether every one parses as an integer, and up to 257 distinct
values (stopping the set there, since every threshold in R4 is below it).

**Rationale**: SC-005 asks for a proposal within five seconds on a million rows. `csv` reads on the
order of a million short rows per second on the machines CI uses; 50,000 rows is a few hundredths
of a second and does not depend on the file's size. The types are proposals the author confirms
(spec, Assumptions), so a bounded sample is honest as long as it is labelled as a sample.

**Alternatives considered**:
- *Read everything*: exact, but time grows with the data and the answer does not change for any
  fixture.
- *Random sampling across the file*: needs a pass to count rows or seeking into the middle of a text
  file; more code for proposals that are confirmed anyway. Order bias is stated in the reason text.

---

## R4. The rules that propose a type

**Decision**: Applied in this order to the sampled values of one column; the first that matches
gives the proposal and its reason, which is shown verbatim.

| # | Condition | Proposal | Reason shown |
|---|---|---|---|
| 1 | every cell empty | leave out | "every sampled cell is empty" |
| 2 | one distinct value | leave out | "one value in every sampled row: carries no information" |
| 3 | values look like image file names (suffix `.png`, `.jpg`, `.jpeg`, `.bmp`, `.pgm`) | leave out, flagged | "file names of images: image inputs are not set up by init yet" |
| 4 | exactly two distinct values | `binary` | "2 distinct values: x and y" |
| 5 | name is `id`, ends in `_id`, or is/ends in `code`, and all values are integers | `category` | "integers in a column named like an identifier: a code, not a magnitude" |
| 6 | not every value numeric | `category` | "text values, N distinct" |
| 7 | all values integers and at most 16 distinct | `category` | "N distinct integer values" |
| 8 | otherwise | `number` | "numeric, N distinct values" |

Rule 5 exists because of `can_id` in the synthetic fixture: 957 distinct integers, which rule 8 alone
would call a number — exactly the mistake feature 008 was built to correct (its Context section and
feature 006, research R11). The 16 of rule 7 keeps small codes (a gear, a mode) as categories while
`dlc` (8 distinct integers 1–8 in the fixture, a length) would also become a category; that is a
proposal the author may overrule, and the reason makes the basis plain.

Measured on the fixtures, accepting every proposal gives: synthetic — `can_id` category, `dlc`
category, `b0`–`b2` number; frames — `c0`–`c7` number; anomaly — `m0`–`m7` number; images — the
`image` column flagged by rule 3, so `init` stops with the pointer to the manifest reference
(edge case "the image input").

**Rationale**: Every rule is a property of the values or the name that a reader can check against
the reason shown, so a wrong proposal is visibly wrong rather than mysteriously wrong. No rule needs
the training extra.

**Alternatives considered**:
- *A ratio of distinct values to rows*: depends on the sample size, so the proposal would change
  with R3's cap.
- *No name rule*: simpler, but the project's own pilot would be proposed wrongly.

---

## R5. Proposing the output column and its type

**Decision**: The proposed output is the first column whose name is one of `label`, `target`,
`class`, `y`, `condition`, `outcome` (in that order of preference); failing that, the last column
whose R4 proposal is `category` or `binary`; failing that, no proposal. The output types offered
follow from the values: non-numeric with two values → `binary` (proposed), `category`, `anomaly`;
non-numeric with more → `category` (proposed), `anomaly`; numeric → `number` (proposed), plus
`category`/`binary` when R4 rule 4 or 7 matched. `anomaly` needs a value meaning normal; it is offered
only when one value is `normal` (the schema's default `normal_label`), or else with a question for the
normal value.

**Rationale**: the fixtures use `label` and `condition`; Ludwig's examples use `label` and `target`.
The output type list is limited to what the schema accepts (`OUTPUT_TYPES`) and to what the values
can mean, so FR-009 holds without a list of special cases per template.

**Alternatives considered**: *always the first or last column* — wrong for two of the four fixtures.

---

## R6. Two ways in, one session

**Decision**: Every question has a command-line option that answers it. The session takes answers
from three sources, in this order: an option given on the command line; otherwise, with
`--no-input`, the proposal (and a usage error, exit 2, naming the option, when there is none);
otherwise the dialogue, which reads one line per question from standard input. When standard input
is not a terminal the dialogue still reads lines from it, so a test or a script can pipe answers;
end of input before the summary is confirmed aborts without writing.

| Question | Option |
|---|---|
| data | `--dataset <path>` |
| output column | `--output <column>` |
| output type | `--output-type <type>` |
| inputs and their types | `--input <column>=<type>` (repeatable; `<column>=-` leaves one out) |
| template | `--template <id>` |
| template parameters | `--params '<YAML flow mapping>'` |
| window | `--window <records>` |
| boards | `--board <id>` (repeatable) |
| budget | `--budget <value>` |
| model name | `--name <name>` |
| file | the positional `<manifest>` |
| overwrite an existing file | `--overwrite` |

**Rationale**: FR-021 (no questions), FR-022 (not a terminal), US3's byte-identical check: an
interactive session and an option-only session must produce the same file, which they do when both
fill the same answer set (data-model.md) and the writer only sees the answer set.

`--overwrite`, not `--force`: `tests/contract/test_no_skip_option.py` forbids `force` in any option
string, and the word would also be wrong here — the option skips no check, it confirms a write.

**Alternatives considered**:
- *An answers file*: a YAML file of answers is a manifest with extra steps; the options are fewer
  concepts.
- *Refuse when standard input is not a terminal*: would make the dialogue itself untestable.

---

## R7. Template starters: proposals that come from the template, not from `init`

**Decision**: `TemplateParameterSpec` gains one optional field, `starter`, a small frozen dataclass:
`params` (a mapping the template's own parameter model validates), `window` (records per window, or
`None` for a template that consumes none), `rank` (an integer: lower is proposed first when several
templates fit) and `note` (one line on when to choose it). The four built-in templates get starters
copied from the shipped examples. A template without a starter is still offered; its parameters are
then asked for as a YAML flow mapping with no proposal, and validated by the template's parameter model
as soon as they are typed.

| Template | `params` | `window` | `rank` | Source |
|---|---|---|---|---|
| `mlp` | `{hidden: [32, 16], dropout: 0.1}` | 64 | 0 | `examples/picket-mlp.yaml` |
| `conv1d` | `{blocks: [{filters: 16, kernel: 5, pool: 2}, {filters: 32, kernel: 3}]}` | 64 | 1 | built so `window_fit` passes at 64 |
| `conv2d` | the two blocks of `examples/frames-conv2d.yaml` | 12 | 2 | `examples/frames-conv2d.yaml` |
| `autoencoder` | `{encoder: [32, 16], code: 4}` | 5 | 0 | `examples/anomaly-autoencoder.yaml` |

The window proposal is the starter's window, raised to the smallest window the template's
`window_fit` or `plane_fit` accepts when the starter's is too short for the author's parameters.

**Rationale**: Every required answer needs a proposal for SC-003 (accept everything in at most 12
answers), and the template parameters (`hidden`, `blocks`, `encoder` and `code` have no default) and
the window (`preprocessing.window_size` has none; every built-in template consumes one) are the
largest. Principle VII says templates are data that register themselves; putting the starter on the
template keeps `init` free of a list of template names (FR-010, SC-006), and a third-party template
can carry one through the same entry point. The field is optional with a default of `None`, like
`window_fit` and `plane_fit`, so no existing template breaks.

The starter is not a default: the manifest still writes the parameters, because the schema requires
them, and `render` shows them as stated. Principle I's ban on defaults outside the template and board
is untouched — this is a proposal shown in a dialogue, not a value resolved when a manifest omits one.

**Alternatives considered**:
- *A table of starters inside `init`*: a central list of template names, which Principle VII and
  FR-010 forbid.
- *Make the parameters optional with defaults*: changes the schema and what every existing manifest
  means; a larger decision than this feature, and not one the owner asked for.

---

## R8. Proposals for the rest

**Decision**:

| Answer | Proposal | Shown as |
|---|---|---|
| boards | none (amended 2026-11-17, review A10): the author picks; at least one is required | the board's RAM and flash, with their sources |
| quantization | `int8` | `none` is offered as "float32, for comparison"; `float16` is not offered (review §3.5) |
| `accuracy_drop_max` | 0.02 | "the value `examples/picket-mlp.yaml` uses — not a recommendation for your model" |
| `auc_drop_max` | 0.05 | same, from `examples/anomaly-autoencoder.yaml` |
| `mae_increase_max` | none | in the column's unit; nothing to copy from an example |
| model name | `<dataset directory>-<template>`, made lower case with every other character replaced by `-` | |
| model version | `0.1.0` | shown in the summary, not asked |
| `representative_samples` | 100, the schema's minimum for int8 | shown in the summary, not asked |
| file | `<model name>.yaml` in the current directory | |

`representative_samples` has no default and int8 requires at least 100 (rule CF-8 of the schema,
`MINIMUM_REPRESENTATIVE_SAMPLES`). It is not a budget, so FR-011 does not require the author to
confirm it; it is shown in the summary, where the author can change it like any other answer.

**Rationale**: Each proposal names its source, so none of them reads as a recommendation (spec,
Assumptions). The smallest board is the honest proposal when the author has not said which board
they have: it is the one most likely to stop the model, and the fit check before training says so
early (Principle V).

**Alternatives considered**: *propose every board* — the picket example names all three, but it
proposes a decision on the author's behalf about hardware they may not own.

---

## R9. Writing the file: comments, no defaults, byte-identical

**Decision**: `caravan.manifest._yaml` gains `dump_commented(document) -> str`, which serialises a
mapping built from `ruamel.yaml`'s round-trip types with comments attached, using fixed settings
(indent 2, width 100, no sorting, flow style for each input feature and for lists of numbers). The
writer in `init` builds that mapping from the answer set only, in the schema's section order, and
omits every key whose value equals what the schema, the template or the board would resolve
(FR-017). The header comment names the dataset and points at `docs/ref/manifest/index.md`; each
section carries one comment line; the ignored columns are listed in a comment above
`input_features`.

The bytes are written to a temporary file beside the target, validated with `load_manifest` — the
same function `caravan validate` calls — and moved into place with `os.replace` only when valid.

**Rationale**: `_yaml.py` is the one module allowed to import the YAML library (its docstring,
Principle XII "a dependency used in one place is isolated behind one module"). `ruamel.yaml`'s
round-trip mode is the part of the library already installed that writes comments. Validating the
exact bytes, not the in-memory answers, is what makes FR-003 true of the file. `os.replace` is atomic
on one file system, so an abort or a failed validation leaves no partial file (FR-004).

**Alternatives considered**:
- *Format the YAML by hand with strings*: no library surprises, but quoting a dataset path or a
  category value correctly is exactly what the library is for.
- *Safe dump plus comments inserted by line matching*: fragile, and still two code paths.

---

## R10. Going back, and errors at the summary

**Decision**: At any question, `<` and Enter goes back one question; at the summary, a question's
number goes to it. After the summary is confirmed and the manifest fails validation (possible only
through a free-form answer such as a third-party template's parameters or a window), the findings
are printed in `caravan validate`'s format and the session returns to the question owning the first
finding's path. With `--no-input`, the same findings end the run with exit 1 and nothing written.

**Rationale**: FR-013, FR-014; and a dialogue that offers only valid choices still has two free-form
answers. Mapping a finding back to its question needs only the path prefix (`model.params` →
parameters, `preprocessing.window_size` → window, `export.targets` → boards, `output_features[0].*` →
budget).

**Alternatives considered**: *write the invalid file and exit 1* — leaves the author with a broken
file, which is what they came to `init` to avoid.

---

## R11. The full-screen interface: Textual, behind the `authoring` extra

**Decision**: The full-screen interface is a Textual application in `caravan/tui/`, installed by the
extra `authoring = ["textual>=…"]` (constitution v4.4.0). It drives the same `Session` as the line
dialogue: it asks the session for the current question, shows its choices as a list (one answer:
radio-style; several: checkboxes) or a form, and hands the chosen answer back. The side panel shows
what the question's `explain` returns — columns, window table and strip, drawing, memory — so the
interface holds no knowledge the line dialogue lacks. `caravan init` starts it when Textual imports
and both standard input and output are terminals, unless `--plain`.

**Rationale**: Textual has lists, selection lists, inputs, scrolling panes and a test pilot that
presses keys without a terminal, so US4's byte-identity test runs in CI. It is pure Python and runs
on 3.13–3.15. One engine, two front ends, keeps FR-025's "same questions, same file" true by
construction.

**Alternatives considered**: *prompt_toolkit* — fine for single prompts; side-by-side panes and
forms are much more work (owner's choice, 2026-11-17). *curses* — no Windows, no test pilot.

## R12. The window recommendation

**Decision**: Candidates are 4, 8, 16, 32, 64 and 128 rows, those that fit the data and the
template's `window_fit`. For each, the data stage's own planner (`plan_windows` with the recordings
and the label rule of feature 014, and the derived split) gives the windows per class in the test
part and the windows lost to mixed labels. The proposal is the largest candidate that loses at most
5 % of its windows and keeps at least 5 test windows of every class; when none does, the candidate
that loses the fewest. The reason names the measure ("label stays the same for at least 32 rows in
your data, so up to 32 rows almost nothing is lost"). The strip shows about 70 rows around the
first change of label, cut into windows, each with the label it learns (`✗` for a lost window).

**Rationale**: the review (§3.3) asked for test counts, not all-split counts, because the test part
decides how finely the int8 gate can measure; using the planner itself means the table cannot
disagree with what `build` later does. Without a sample period the proposal is a data-availability
guess and says so.

## R13. Memory before building

**Decision**: From the inputs, the window, the template and its parameters, `caravan/init/memory.py`
produces the `LayerRecord`s the built model would have — the frontend's channels (1 per number or
binary column, the embedding cap per category column), then the template's layers as its builder
makes them — and passes them to `targets.fit.floors` and `verdicts`, the functions `build` uses. The
output layer's width is the number of classes the data shows. The panel prints, per board, flash and
RAM floors against the board's figure with a bar, `✗` where a floor exceeds it, and the line
"lower bounds, estimated before building; build checks them again".

**Rationale**: the same floors as `build` (Principle IV: one labelled number, not two methods); no
framework needed. A test builds every starter with the training extra and checks the estimate equals
`build`'s floors (train suite).

## R14. The parameter form

**Decision**: The form is generated from the template's pydantic model: an `int`/`float` field is a
number input with its bounds; a `Literal` is a choice; a `bool` a checkbox; an optional value has an
"unset" choice; a `list[int]` is one row per entry; a `list[<model>]` is one row per block with a
field per value. Rows are added (copy of the last) and removed (never below the minimum length).
Presets are the template's starter and two scaled variants (half and double the widths/filters).
Every change revalidates the whole model and shows the first error at its field. The line dialogue
asks the same fields one by one, with `+`/`-` to add or remove a row.

**Rationale**: FR-033; works for third-party templates without code in `init` (Principle VII).
