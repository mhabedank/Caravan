# Specification Quality Checklist: Documentation organised like Django's

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-29
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs) — the build tools are named once, in
      Assumptions, as a constraint the owner stated; no requirement depends on them
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders — dotted field names such as `export.targets` are the
      reader's own vocabulary, not implementation
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — the open choices had defaults the owner's
      decisions and Django's model settle: the overview is a page of its own (FR-001), the manifest
      reference splits by top-level section (FR-008), two how-to guides to start (FR-007)
- [x] Requirements are testable and unambiguous — FR-022's no-hedging rule names the constructions
      it forbids, so a review can check it
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details) — SC-008 names the CI job
      because the constitution bounds that job, as feature 011's SC-007 did
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded — "Out of scope" names what is moved and linked but not rewritten
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

Three requirements are the ones most likely to be weakened under pressure, and are worth checking
at every later phase:

1. **FR-010** — deep links into the old manifest page must keep reaching their field. It is the
   one forward that a page-level redirect does not give for free.
2. **FR-014** — an unresolved name fails the build. Without it, linking decays the first time a
   field is renamed, and nobody notices.
3. **FR-027** — no new test suite. The owner removed one in feature 010 (D5); the build's strictness
   is the check.
