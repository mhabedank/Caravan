# Specification Quality Checklist: Build and Train

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
- [x] Success criteria are technology-agnostic (no implementation details)
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

**The one open clarification is answered** (2026-10-22, by the author).

- **FR-010 — the dataset's on-disk format**: raw, record-level delimited text, windowed inside
  this feature. Of the three readings, this is the only one under which `dataset.window` is a
  promise the tool can keep rather than a claim about work done elsewhere. It is now FR-023 to
  FR-025, with the two conventions it forces — the `label` column, and discarding a window whose
  records disagree about the label — recorded in Assumptions with their alternatives and their
  cost. A registry of per-kind loaders was not adopted: one format, specified, until a second
  model needs a second one.

**One item passes with a qualification**, the same one as in feature 001:

- "No implementation details leak": the spec names the `train` extra's Python window (3.13) and
  the reason. That is not a choice this feature makes — it is a constitutional obligation from
  v2.2.0 restated so it can be tested here, and the fact that a framework publishes no wheel for
  a supported Python is a product constraint rather than an implementation detail. No requirement
  names a library, an API shape or a code structure. Marked unchecked rather than checked, so the
  qualification is visible rather than buried in this note.

**Four decisions the spec takes rather than asks about**, all recorded in Assumptions because a
reasonable default exists and the cost of being wrong is low:

- the quality metrics are a fixed documented set for classification, with no manifest field yet;
- building reads the dataset's shape but not its contents, so the input shape has one source of
  truth;
- the label column is named `label` and every other column is a feature, by convention rather than
  by a new manifest field;
- a window whose records disagree about the label is discarded and counted, rather than labelled
  by majority or by its last record. This is the one of the four worth objecting to if the ported
  model needs those boundary windows — it is named in Assumptions as the decision to revisit.

**What the analysis pass changed in this spec** (2026-10-22, after plan and tasks, before any code):

- **FR-021 was stated against a mechanism that does not exist.** It required the extra to "declare
  its own Python window"; packaging has no such thing. It now names what the window actually is —
  a floor that admits it, a marker on every dependency, a message when a stage runs outside it, and
  every admitted version tested.
- **FR-011's second clause was incoherent and is gone.** It asked for the data's feature width to be
  checked against "the number the manifest's window implies", and the manifest implies no feature
  width. Rule DS-7 was withdrawn for the same reason — the second time a rule turned out to be
  entailed or unreachable once the schema was written, after CF-5 in feature 001.
- **FR-006a was added**: which splits the metrics are measured on was never stated. They are
  measured on `val` and `test` and never on the training split.
- **FR-024's unreachable half is named as unreachable**: no manifest can ask for "no window" while
  the only registered template requires one, so that path is proven by a direct test of the rule.
- **FR-013's wording was malformed** ("No dataset MUST be written") and is now a proper prohibition.
- **User story 2's "answer in seconds" was overstated**: `build` hashes the dataset once, about a
  second per gigabyte, because the dataset's version is part of what identifies the result.

**One honesty constraint worth re-reading before implementing**: the spec deliberately does *not*
promise bit-identical training from the same seed. Thread counts, kernel implementations and
hardware make that untrue in general. Bit-exactness becomes a meaningful promise at the quantized
model, which is the next feature.
