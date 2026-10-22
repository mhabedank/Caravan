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

**One verified fact the planning phase must not re-litigate**: there is no conversion path that
avoids the training framework today — the standalone runtime package is a runtime, not a
converter (checked 2026-10-22). So conversion stays on the Python the training extra needs, and
the published floor stays where feature 002 put it. What *is* open for the plan is whether the
measurement half can carry the later stages too, which is why it is a separate extra here.
