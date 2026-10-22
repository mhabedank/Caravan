# Specification Quality Checklist: Quantize

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [ ] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Notes

**Two items are unchecked with a qualification, the same pair as in feature 002**, and both are
left visibly unchecked rather than checked with a footnote:

- **"Success criteria are technology-agnostic"**: SC-008 and SC-010 say "no training framework
  installed". That is not a technology choice this feature makes — it is the layering rule of
  Principle XII, which is what the feature exists to extend to the second half of the pipeline,
  and it has to be stated in a form a test can check.
- **"No implementation details leak"**: user story 2 quotes a converter's log line,
  `fully_quantize: 0`. It is there because it is the *evidence* for the requirement that follows:
  a tool printed that while producing a fully quantized model, so the stage may not read a log as
  a verdict. Removing the quote would leave FR-006 looking like caution for its own sake. No
  requirement names a library, an API shape or a code structure.

**No clarification was needed, and five decisions were taken instead** — all recorded in
Assumptions with their alternatives, all reversible, and none of which would make the work useless
if the author disagrees:

1. the measurement part is a second extra rather than part of the training extra;
2. calibration is capped by what the training split holds, with all three counts recorded, rather
   than refused;
3. `accuracy_drop_max` is read as an absolute difference, as the schema writes it;
4. on the committed fixture the acceptance test asserts the gate's *mechanism* rather than a
   particular accuracy, because the fixture's test split gives the gate a resolution of one
   prediction in twelve;
5. the float accuracy is re-measured here rather than read from the training report, so the
   comparison is between two numbers taken the same way.

**The decision most worth a second opinion** is the fourth. A gate whose resolution is coarser
than its threshold is a gate that cannot really be exercised on the fixture, and the honest options
were to assert the mechanism (chosen), to grow the fixture past its 200 KB limit, or to give the
fixture manifest a wider threshold than the pilot's from the start. The third is held in reserve
and only taken if quantization does flip a prediction, with the reason written in the file.

**What the analysis pass changed** (2026-10-22, after plan and tasks, before any code). Seven
findings, all fixed; two of them would have cost real time:

- **The reuse matrix had no task at all.** FR-020 to FR-022 and SC-007 were written, the seven
  cases were in the quickstart, and nothing implemented a test. In feature 002 the equivalent was
  the most important test in the feature. Now T029a (the seven lived cases) and T029b (one line
  that adds this stage to feature 002's generic projection test, after which no schema field can
  quietly enter or leave what re-quantizes).
- **A valid manifest would have crashed.** `representative_samples` is `int | None` and rule CF-4
  demands it only for int8, so a `float16` or `none` manifest legitimately has none — and the
  calibration plan computed `min(requested, available)`. That is `min(None, 56)`: a `TypeError`,
  exit 3, "a defect in caravan itself", on correct input. Checked against the schema rather than
  assumed. FR-005 now says an absent count is valid input and never an error.
- **Q-1's "missing model" half was unreachable**, the same shape as DS-7 in feature 002: the stage
  runner guarantees the upstream ran and a cache entry with absent artifacts counts as a miss, so
  the file is always there. Narrowed to *unreadable*, which a corrupt cached file does reach.
- **FR-018 and FR-019 had no owner**: nothing was assigned the `tools` record or the trained
  model's size, since the inspection only ever sees the quantized file. Both named in T021.
- **Where the error table is written was unstated, and it mattered**: a failing stage's working
  directory is deleted by the runner — that is how a failed gate leaves no model — so a table
  written there would be destroyed by the mechanism meant to protect the artifact. It goes straight
  into the run directory.
- **"Regenerate byte-identically" was the wrong promise** for a committed example model: a
  flatbuffer carries its converter's version and layout choices and nothing promises two runs are
  identical. The test asserts functional equivalence — tensor types, shapes, quantisation
  parameters, predictions — and lives in `tests/train`, because regenerating needs a converter.
- **`resolution` was required by both contracts and by a task but absent from FR-013.** Added:
  a verdict whose resolution is coarser than its threshold is still the verdict, and must be
  readable as such.

**What the implementation found, and it is a correction to this spec rather than to the code.**
FR-023 said reading and running an exported model "works on every Python version the project
supports". It does not: the runtime publishes cp310 through cp314 and **no cp315**, in 2.3.0 and
every recent version. The claim came from verifying cp314 during planning and assuming the next
tag followed — one step of inference past the evidence, in a project whose whole method is not to
take that step.

It is corrected everywhere it was said: the requirement, the success criterion, the user story, the
research note, the plan, the extra's marker, the continuous-integration matrix, the budgets page,
the README, the constitution's Technical Baseline, and the test that had *forbidden* the marker
reality requires. The window is now stated with its evidence and its closing condition, like the
conversion half's, and a CI step fails the build if the runtime ever resolves on 3.15 while the
marker still excludes it.

The case for the second extra survives, because it never rested mainly on Python coverage:
114 MiB against 1,971, no training framework in its graph, and not built on an interpreter its own
vendor has announced for deletion. Reaching two of three Pythons instead of one is a bonus, and
calling it "everywhere" was the error.

**One verified fact the planning phase must not re-litigate**: there is no conversion path that
avoids the training framework today — the standalone runtime package is a runtime, not a
converter (checked 2026-10-22). So conversion stays on the Python the training extra needs, and
the published floor stays where feature 002 put it. What *is* open for the plan is whether the
measurement half can carry the later stages too, which is why it is a separate extra here.
