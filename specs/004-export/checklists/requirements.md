# Specification Quality Checklist: Export

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

**The same two items are unchecked as in features 002 and 003**, for the same reasons, and are
left visibly unchecked rather than checked with a footnote:

- **"Success criteria are technology-agnostic"**: SC-004 says the C array compiles standing alone
  and SC-009 says the proving half runs with no training framework installed. Neither is a
  technology preference this feature expresses. The first is the content of Principle VIII's
  no-lock-in promise — an artifact usable without Caravan — and the second is the layering rule of
  Principle XII. Both have to be stated in a form a test can check.
- **"No implementation details leak"**: the Assumptions section quotes a converter error,
  `variable != nullptr was not true`, and names the two conversion paths. It is there as the
  *evidence* for a decision, in the same way feature 003's `fully_quantize: 0` was: one obvious
  way of fixing the input batch does not work, and the next person to have the idea deserves the
  three lines rather than the afternoon. No requirement names a library, an API shape or a code
  structure.

**No clarification was needed. One item is deliberately left open for the plan, and six decisions
were taken** — all in Assumptions with their alternatives, all reversible.

**The open item is the working-memory figure, and it is open against the constitution**, which is
why it is in its own paragraph under Constitution Alignment rather than buried in Assumptions.
Principle VIII requires the export to document "the tensor arena size it requires"; no desktop tool
can supply that figure, because the runtime plans that memory with its own allocator on the target
and the analysis tool available here reports model and buffer sizes and no arena (checked
2026-10-22). The specification takes the honest position — document a floor, label it a floor, and
say which stage establishes the real figure — and records that if the principle means a measured
number, the principle needs an amendment naming the stage that can honestly produce it. The plan's
constitution check decides which of the two, and either way the decision is written down. This is
flagged rather than resolved here because it is a governance question, not a design one.

**The six decisions:**

1. the batch is fixed at conversion by cloning the trained model, not at build time, so training
   keeps the dynamic batch it needs;
2. feature 003's recorded numbers change as a consequence, which is accepted, because the
   alternative is a gate that measured a graph other than the one that ships;
3. the operator set is read through the schema binding that already ships with the runtime extra,
   rather than vendoring one;
4. coverage is a sourced, dated table per accelerated library — the weaker claim "the library
   supplies a kernel for this operator", not the stronger "this kernel will be selected", which
   needs the toolchain;
5. the runner skeleton is emitted and not compiled, because nothing here can compile it and
   asserting otherwise would be an unverified claim;
6. `onnx` stays in the schema and is refused by name, rather than being removed from the schema or
   silently ignored.
