# Specification Quality Checklist: `caravan init` Proposes the Whole Manifest at Once

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-11-24
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
- [x] No implementation details leak into specification

## Notes

- Iteration 1 (2026-11-24): two markers remain, both owner decisions the request itself left open —
  FR-006 (memory per board in the proposal) and FR-019 (whether the full-screen interface stays).
  The third open point of the request, whether the constitution must be amended, is answered in the
  spec's Constitution section (yes, for the `AGENTS.md`; after iteration 2 also for the extras
  slot of the removed full-screen interface), not left as a marker.
- Content quality: the spec names the command line, its options, standard output and standard error,
  and the JSON document. For a command-line tool these are the user-facing interface, not
  implementation; no language, library or module is named outside the quoted request.
- Iteration 1 fixed one internal contradiction: FR-002 defined "certain" as "the data leaves one
  answer", which a four-valued text output (category or anomaly) never satisfies, while FR-003
  measured certainty against the shipped data. FR-002 now defers to FR-003's operational test.
- Iteration 2 (2026-11-26): both markers answered by the owner and recorded under Clarifications.
  FR-019: the full-screen interface is removed with the `authoring` extra (no `--tui`); User Story 5,
  FR-018 to FR-020, FR-024, FR-030, FR-032 and the Constitution section follow, and SC-010 measures
  it. FR-006: one line per chosen board with the lower bounds and a mark where one is exceeded; User
  Story 1 (scenarios 7 and 8), FR-022 and the Principle IV and V notes follow. No marker remains;
  every item passes.
- Planning (2026-11-27) amended two requirements from measurements (research R1): FR-002 lists the
  budget of a `number` output as open (no shipped value carries over its unit), and FR-003 measures
  the window against the window table's criteria, because the shipped manifests' sizes predate the
  table and fail its criteria where they differ from the proposal. Every item still passes.
- Analysis (2026-11-27) fixes: FR-007 asks open items as well as uncertain ones; FR-015 and SC-005
  name the one placeholder exception; FR-002 lists the normal value as open; FR-003 names which
  datasets count; FR-027 asks for the program-readable form (`render --stdout`); the template's
  certainty when only one answers is in the Assumptions; FR-020 points to SC-010 instead of repeating
  it; US1 scenario 7 labels the bounds in the board question (Principle IV). Constitution v4.5.0 now
  admits the `AGENTS.md` (T001). Every item still passes.
