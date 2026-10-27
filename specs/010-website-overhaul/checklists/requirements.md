# Specification Quality Checklist: A website that teaches Caravan in half an hour

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-27
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

## Validation notes (iteration 1)

**Content quality.** The spec names no site generator, theme, template engine, CSS approach or
hosting product. The "Context" section describes the present site by what a reader meets (a default
theme, six-column tables, a 93-line page) rather than by the tooling that produces it, which is
what makes the problem legible to a non-technical reader. Page and file names that already exist
(`try-it.md`, `docs/`) appear only in that diagnosis of the current state, not in any requirement.

**Testability.** Each of FR-001..FR-044 states an observable property of the published site or of
its checks. The three softest were tightened before this pass:
- "explain" was given a test everywhere it appears (FR-018, FR-020): expansion at first use, and
  the four things a setting's prose must cover.
- "one design language" was made checkable by requiring it to be written down to a stated level of
  precision (FR-027), not merely applied.
- "no references" was given a mechanical test (SC-010, SC-011): a search of the published site.

**Measurability.** The user's three headline numbers are the spec's three timed criteria
(SC-001/002 for three seconds, SC-003 for fifteen minutes, SC-004 for thirty), each with a sample
size, a pass threshold and a stated start line. The start lines are in Assumptions because
the fifteen-minute promise is otherwise untestable against a 1.9 GiB download — the spec requires
the weight to be disclosed rather than hiding it inside the claim.

**Technology-agnostic criteria.** No criterion names a tool. SC-012 cites the AA contrast level of
the published accessibility guidelines, which is a user-facing threshold rather than an
implementation choice. SC-014 and SC-015 describe check outcomes ("fails rather than publishing",
"builds offline") without naming the checker.

**Constitutional constraints carried into requirements**, so planning does not have to rediscover
them:
- provenance labels on every hardware figure, a marketing page counting as a published table
  (FR-006, FR-038, SC-016, and User Story 3 scenario 4);
- no hosted service and no accounts to build or read the site (FR-042, FR-044, SC-015);
- documentation-only changes must not spend the code test matrix (FR-043);
- no new runtime dependency on the package from the site's own build (FR-042).

**Scope boundaries.** Assumptions fix four edges the description left open: the pipeline's behaviour
does not change, the site stays in English, the example dataset remains the series' opener, and the
existing build checks are a floor rather than a starting point to renegotiate.

## Validation notes (iteration 2, 2026-10-27)

The owner answered all three questions with the recommended option. The spec now carries them as
D1, D2 and D3 under "Decisions taken", each naming the requirements that implement it, and every
[NEEDS CLARIFICATION] marker is gone. The requirements were renumbered to FR-001..FR-046 for the two
clauses the answers added; the only two cross-references in the document both point at FR-026, which
kept its number.

**What the answers added rather than merely settled:**
- D1 needed a second clause. "Restrained" and "not overdone" are the owner's words and are not
  testable as written, so FR-027 names what is excluded (scan lines, screen curvature, blinking
  cursors, decorative glitch, pixel type in body text) and requires the site to state once what the
  register stands for. Without that, "professional 8-bit" is a matter of taste rather than a
  property anyone can check.
- D3 opened a gap and FR-038 closes it. D2 keeps the firmware build the pipeline already has, but
  that build is for the withdrawn board, so after this feature nothing would verify the path the
  site teaches. The spec records the gap where it was created instead of leaving planning to find
  it.
- FR-008 became testable. "Not a tutorial" says what the series is not; the requirement now says
  what it is — parts called legs, numbered, each title naming what the reader ends with.

**Re-checked after the edit**: all mandatory sections present; FR numbering sequential and complete
(46, verified mechanically); no implementation detail introduced by the answers — "generic ESP32
development board" is hardware the reader buys, and the 8-bit register is design intent, neither
being a technology choice the spec is forbidden to make; the two cross-references still resolve.

**Still open by design, for `/speckit-plan` rather than the spec:** which check closes the FR-038
gap; whether the generated ESP32 runner skeleton suffices as the deployment leg's starting point;
how many legs the series has and where the fifteen-minute mark falls between them.

## Validation notes (iteration 3, 2026-10-27)

D1 was reopened and replaced. The owner was not certain about the 8-bit direction, preferred the
Mobility Model Zoo's existing identity, and chose it with Sphinx retained and a sibling rather than
twin relationship to the zoo. The design block was rewritten (now FR-026..FR-038) and every
requirement renumbered to FR-001..FR-050; the five prose cross-references were repaired by what
they point at rather than by their old numbers, and each was re-verified after renumbering.

**What reading the zoo's identity added to the spec, beyond the swap:**
- FR-028 exists because of a constitutional constraint, not a preference. Caravan must not depend
  on the zoo, so the identity can only arrive as a copy: no shared package, no submodule, nothing
  fetched at build time. The licence obligation travels with it (the typefaces are OFL-1.1 and
  need their notice), and the spec states that the two identities may drift once copied.
- FR-030 encodes a lesson the zoo paid for. Its own identity feature records that moving only the
  mark and the motifs into the poster world made the remaining interface colours read as foreign
  bodies, and that a half step is worse than either whole. That is why 8-bit is dropped entirely
  rather than kept for the figures.
- FR-029 exists because the design would otherwise contradict the project's stated position. The
  constitution says Caravan may be used outside the zoo; a site indistinguishable from the zoo's
  would read as a subproject. Its own mark and its own reservation for the single accent keep the
  position visible in the design.
- FR-034 and SC-012 were strengthened. The zoo measures contrast in a browser on the rendered page
  in both schemes, having learned that a palette table is not where the defect appears. The
  criterion now requires the same, so "meets AA" is a measurement rather than an intention.

**One qualification on "no implementation details".** No requirement names a technology. The
Decisions section and the Assumptions do name the site generator, because the owner's answer named
it: keeping it was part of the decision taken, and a spec records the constraints it is given. The
requirements remain expressed as properties of the published site, so planning still chooses how
each is met.

**Re-checked after the edit**: 50 requirements, numbering sequential and complete (verified
mechanically); no [NEEDS CLARIFICATION] markers; all five cross-references resolve; 8-bit survives
only in the verbatim input quote and in the record of what D1 superseded, which is deliberate.

**Still open by design, for `/speckit-plan`:** which check closes the FR-042 verification gap; how
far the copied identity's prose layer has to be adapted to the generator's markup; what the single
warm accent is reserved for in Caravan; how many legs the series has and where the fifteen-minute
mark falls between them.

## Complete

All checklist items pass. The spec is ready for `/speckit-plan`.
