# Specification Quality Checklist: The conv1d Template

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

**The same two items are unchecked as in features 002, 003 and 004**, for the same reasons, and are
left visibly unchecked rather than checked with a footnote:

- **"Success criteria are technology-agnostic"**: SC-008 says the parameter half validates manifests
  "in an installation with no training framework". That is the layering rule of Principle XII, not a
  technology preference this feature expresses, and it has to be stated in a form a test can check.
- **"No implementation details leak"**: the Assumptions section names a framework's layer types and
  the operators they convert to. They are there as the *evidence* for three decisions — why the head
  is a parameter, why normalisation is offered, why separable convolution is not — and each is a
  measurement with its date. Removing them would leave three choices looking arbitrary. No
  requirement names a library, an API shape or a code structure.

**One thing deliberately written as prose rather than as a requirement.** The spec says the
template must express "a sequence of convolution blocks" (FR-006) without fixing how many, what the
defaults are, or the exact parameter names. That is the plan's job: the shape of the parameter model
is a design decision with alternatives, and writing it into the specification would be deciding it
without the reasoning.

**No clarification was needed, and six decisions were taken** — all in Assumptions with their
measurements, all reversible:

1. the template is named and described in one dimension although the runtime converts to two,
   because the author is describing a model and not a kernel;
2. the head is a parameter rather than a fixed choice, because the trade it makes is real in both
   directions and measured;
3. normalisation inside a block is offered, because it folds into the convolution and is free at
   inference;
4. separable convolution is measured but not offered, because no named model needs it yet — and the
   measurement is recorded so the next one does not repeat it;
5. the committed synthetic fixture is the acceptance dataset, and the named model's shape is checked
   by building rather than by training;
6. nothing here claims an accuracy or a latency for a model built through this pipeline, because
   none has been trained on real data yet.
