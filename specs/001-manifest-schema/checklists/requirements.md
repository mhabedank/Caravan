# Specification Quality Checklist: Manifest Schema and Package Skeleton

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
- [x] No implementation details leak into specification

## Notes

Two items passed only after the spec was corrected, and two pass with a stated qualification.

**Corrected during validation** (first pass left a rule undecided, which fails "testable and
unambiguous"):

- A split part of zero: the spec said "accepted or rejected according to one stated rule" without
  stating it. Now decided — rejected, because a part with no data cannot be trained on, tuned on
  or evaluated against. FR-017 carries the rule.
- An existing run artifact: the spec said "handled by one stated rule rather than by silent
  overwriting" without stating it. Now decided — each invocation writes into its own new run
  directory and never overwrites or removes an artifact. FR-012 carries the rule.

**Passing with a qualification**:

- "No implementation details (languages, frameworks, APIs)": the spec names the Python version
  policy (FR-031), the YAML manifest format and the Apache-2.0 licence. None of these is a choice
  this feature makes — the language, the manifest format and the licence are fixed by the
  constitution's Technical Baseline and by its licence decision, and FR-031 restates a
  constitutional obligation so that it is testable here. The distribution and command names
  (FR-029) are product identity, not implementation. No requirement names a library, an API shape
  or a code structure.
- "Success criteria are technology-agnostic": SC-003 and SC-008 refer to "no machine-learning
  framework installed" and to continuous integration. The first is a category, not a product, and
  it is the measurable form of the constitution's layering rule — the promise being tested is
  "installs and runs on an ordinary laptop in seconds", which cannot be stated without referring
  to what is absent. The second names where the check runs, not how it is built.

**Post-analysis, 2026-10-22**: the cross-artifact consistency analysis found 19 items across
spec, plan and tasks. Eighteen were fixed in place — two constitution gaps (the run report was
missing the dataset and template provenance fields Principle III names; the board description was
missing the `toolchain` value Principle VII names), two task-level contradictions (the fixture
coverage test would have failed by construction over rules that cannot have manifest fixtures, and
one fixture was assigned to both `valid/` and `invalid/`), two zero-coverage requirements (FR-005
and SC-001, now T062 and T063), and the rest spec and plan drift. One item is left open on purpose
and is the owner's to decide: Principle VI requires every dataset reference to resolve to a
declaration, which this feature defers by design, and no artifact yet names the feature that
honours it.

**Open for review** (not a checklist failure, an owner decision recorded in Assumptions):

- Board descriptions are pulled into this feature as data with a schema, so that a target name can
  be checked and a typo fails early. The alternative was to defer boards entirely and accept any
  string as a target. If the owner prefers the smaller cut, FR-023 to FR-025 and the board parts of
  SC-002 move to the analysis feature.

---

## Requirement coverage after implementation (T060, 2026-10-22)

All 32 functional requirements are covered by a named test or by a named continuous-integration
job. Where a requirement is satisfied structurally rather than by a runtime check, that is stated
rather than papered over.

| Requirement | Covered by |
|---|---|
| FR-001 validate command | `contract/test_cli_contract.py::test_a_valid_manifest_exits_zero`, `integration/test_validate.py` |
| FR-002 actionable rejection | `unit/test_errors.py` (field path first, accepted list, suggestion) |
| FR-003 unknown fields rejected | `unit/test_errors.py::test_unknown_field_lists_what_is_accepted_and_suggests_the_nearest`, fixtures `unknown-field*.yaml` |
| FR-004 exit status distinguishes a rule from a defect | `contract/test_cli_contract.py` (all four codes, including the synthetic defect) |
| FR-005 no option skips a check | `contract/test_no_skip_option.py` |
| FR-006 input untouched, no network | `integration/test_input_untouched.py`, `contract/test_no_network.py` |
| FR-007 declared version; absent is oldest | `unit/test_migration.py::test_a_manifest_without_a_version_is_the_oldest_known_one` |
| FR-008 migration in memory | `unit/test_migration.py::test_an_older_manifest_is_migrated_in_memory` |
| FR-009 unknown version refused, naming implemented | `unit/test_migration.py::test_an_unknown_version_is_refused_and_names_what_is_implemented` |
| FR-010 both versions recorded | `contract/test_run_report.py::test_both_schema_versions_are_present_even_when_equal` |
| FR-011 resolved manifest written | `integration/test_render.py::test_the_resolved_manifest_has_no_implicit_values` |
| FR-012 artifact beside a report with provenance | `contract/test_run_report.py` (field set and order), `integration/test_validate.py` (dataset and template) |
| FR-013 determinism, report exempt | `integration/test_render.py::test_resolving_twice_is_byte_identical`, `contract/test_run_report.py::test_two_reports_of_one_input_differ_only_in_run_identity` |
| FR-014 defaults from schema and template only | `unit/test_schema_requirements.py::test_a_defaults_section_is_not_accepted`, `integration/test_render.py` (template default expanded) |
| FR-015 compliance required | `unit/test_schema_requirements.py::test_a_manifest_without_compliance_is_invalid` |
| FR-016 publication needs complete compliance | **Entailed, not a runtime rule.** `compliance` is required for every manifest and each field rejects an empty value, so no manifest can pass the section and still fail this. Recorded as `ENTAILED_RULES` in `errors.py` and enforced in the other direction by `unit/test_fixture_coverage.py`, which fails if a fixture claims CF-5. |
| FR-017 cross-field rules | `integration/test_validate.py::test_every_invalid_fixture_fires_its_own_rule`, one fixture per rule |
| FR-018 split as named parts | `unit/test_schema_requirements.py::test_a_positional_split_is_not_accepted` |
| FR-019 identity form stated on rejection | `unit/test_errors.py::test_identity_rejection_states_the_required_form` |
| FR-020 dataset reference, shape only | `integration/test_validate.py` (`unresolved` carries the reference with its reason) |
| FR-021 template registry extensible | `unit/test_schema_requirements.py::test_a_second_template_can_be_registered_without_editing_a_central_list` |
| FR-022 unknown template lists registered | fixture `t-1-unknown-template.yaml`, `unit/test_errors.py` |
| FR-023 boards as data; unknown board lists known | fixture `b-1-unknown-board.yaml`, `unit/test_board_schema.py` |
| FR-024 board values and their citations | `unit/test_board_schema.py::test_every_value_needs_a_citation` |
| FR-025 emulator stated honestly | `unit/test_board_schema.py` (omitted, non-existent platform, and the shipped files) |
| FR-026 no training framework in the core | `layering/test_no_framework_imported.py`, `layering/test_hostile_import.py`, `layering/test_declared_dependencies.py` |
| FR-027 install budget checked automatically | the `install-budget` job in `.github/workflows/ci.yml`; measured figures in `docs/budgets.md` |
| FR-028 dependency and extras budget | `layering/test_declared_dependencies.py` (both limits) |
| FR-029 distribution and command names | `layering/test_declared_dependencies.py::test_the_distribution_declares_its_identity_and_its_python_policy` and `::test_the_command_is_installed_under_the_name_the_constitution_fixes` |
| FR-030 Apache-2.0 in metadata | same test, plus the `LICENSE` file |
| FR-031 Python policy, no undocumented upper bounds | same test (`Requires-Python`), `::test_no_upper_version_bound_without_a_documented_incompatibility`, and the CI matrix |
| FR-032 stated data terms, enforced and marked | fixture `cf-8-benchmark-only-publish.yaml`, `integration/test_validate.py` (the `dataset-terms` entry under `unresolved`) |

Success criteria: SC-001 `integration/test_validate.py::test_a_verdict_arrives_in_under_two_seconds` ·
SC-002 `unit/test_fixture_coverage.py` with `integration/test_validate.py` ·
SC-003 the `install-budget` job, measured at 3.1 s and 9 MiB ·
SC-004 fixture `picket-mlp.yaml` validates and renders ·
SC-005 `integration/test_render.py` ·
SC-006 `unit/test_migration.py` ·
SC-007 `integration/test_render.py` ·
SC-008 the `clean-environment` job, verified by hand in a clean environment on 2026-10-22.

**One finding from implementation**, recorded here because it changes what the artifacts claim:
CF-5 cannot fire, for the reason given against FR-016. It was moved out of the rejection-rule set
into `ENTAILED_RULES` with its reasoning, which is the same class of problem the consistency
analysis found with D-1, E-1 and S-1 — a rule identifier that no manifest fixture can ever
exercise. The fixture-coverage test now fails in both directions, so the next one is caught
automatically.
