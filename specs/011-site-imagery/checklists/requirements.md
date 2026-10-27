# Specification Quality Checklist: Imagery for the site

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-27
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain — **one open: FR-031**, whether the generated images
      replace the hand-drawn SVGs, sit beside them, or take only the places the SVGs do not cover.
      Left open deliberately: it is the owner's call, it changes what gets placed rather than what
      gets rendered, and nothing in stories 1–3 is blocked by it.
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded — the "Out of scope" section names what the zoo has and this does not
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

Two things the spec states that are worth repeating before planning:

1. **The rendering cannot be done in the session that wrote this.** The GPU machine is behind a
   VPN that session cannot reach, and its own container has no GPU. Stories 2 and 3 are written to
   be run by the owner, on their machine.
2. **A draft already exists** under `scripts/imagery/` on this branch: the series file with the
   twenty subjects, the generator, the Dockerfile and both pages. It is material for the plan to
   work from, not a decision the plan must accept — in particular the twenty subjects are a
   proposal, and the subject page in story 1 exists so they can be argued with cheaply.

Three requirements are the ones most likely to be weakened under pressure, and are worth checking
at every later phase: FR-008 (nothing is added to the distribution), FR-019 (no provenance, no
placement) and FR-029 (the weight budget is measured, not asserted).
