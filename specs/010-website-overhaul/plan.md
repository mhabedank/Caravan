# Implementation Plan: A website that teaches Caravan in half an hour

**Branch**: `010-website-overhaul` | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-website-overhaul/spec.md`

## Summary

The site is rebuilt around a reader's first half hour: a first screen that answers in three
seconds, then four legs that reach an int8 model by fifteen minutes and an answering board by
thirty, each leg ending in something the reader can point at. The reference pages stop being
six-column tables and start explaining what a setting does and when to change it. The owner's
personal development board comes off the site, and the project's internal development artifacts
with it.

The visual language is copied from the Mobility Model Zoo's screenprint identity rather than
invented (D1, D4), and it arrives as a theme of Caravan's own — Sphinx stays the generator, and
nothing is fetched from the zoo at build time, because Caravan must not depend on it. The
deployment leg targets a generic ESP32 board, built from the firmware that already exists for the
withdrawn one, and the firmware workflow that already blocks releases gains that build so the
documented path is verified before anything ships.

Two findings in [research.md](./research.md) decide the shape and cut the cost. Sphinx's templating
is Jinja2, the same as the zoo's generator, and the zoo's stylesheet is element rules plus utility
classes rather than markup-bound selectors — so the identity ports as a theme with no new
dependency. And the withdrawn board is itself an ESP32, so the generic firmware is the existing 198
lines of inference with its display calls replaced by serial output.

## Technical Context

**Language/Version**: Python 3.13 for the site build and its checks. C++17 for the firmware
example, built with PlatformIO and ESP-IDF. No change to `src/caravan/`.

**Primary Dependencies**: the pinned `docs` group as it stands (`sphinx==9.2.0`,
`myst-parser==5.1.0`); a new pinned group for the browser audit (a browser driver and a vendored
auditing library, R7). **No runtime dependency and no extra is added to the distribution**, and
the theme adds nothing to install at all — it is templates and static files under `docs/`.

**Storage**: none. The site is static files; the firmware's model is a C array in its own source.

**Testing**: `pytest` for the checks that compare pages with the code; the site build with every
warning an error; a browser audit of every page in both colour schemes; a PlatformIO build of both
firmware projects in continuous integration.

**Target Platform**: the published site on GitHub Pages, and a reader's machine offline. The
firmware targets PlatformIO's `esp32dev`.

**Project Type**: a documentation site plus one firmware example, inside an existing command-line
project. No application tier, no service.

**Performance Goals**: the reader's clock, not the machine's — the benefit understood in three
seconds, an int8 model by fifteen minutes, a board answering by thirty (SC-001 to SC-004). The
site's own build stays inside the documentation job it already runs in.

**Constraints**: nothing fetched from the zoo at build time; no account, key or network needed to
build and read the site locally; every figure about hardware carries its provenance label; a change
that touches only the site must not start the framework matrix.

**Scale/Scope**: thirteen existing pages become a landing page, four legs, and a reference set
rewritten to explain rather than tabulate. One new firmware project (~250 lines, mostly derived).
Two workflows touched. Roughly 450 lines of copied stylesheet and two typefaces vendored.

## Constitution Check

*Verified before Phase 0, and again after Phase 1 — see "Post-design re-check" below.*

Principles this feature touches, and how it complies:

| Principle / section | How this feature complies |
|---|---|
| **II. Embedded Targets Only** | The site's new marketing surface states the same narrow scope it states today, after the benefit rather than before it (FR-004). The landing page claims nothing about cloud, desktop or language models. |
| **IV. Measured, Emulated or Estimated — Always Labeled** | A marketing page is a published table for this purpose. Every hardware figure on the site carries exactly one label (FR-006, FR-044, SC-016). The deployment leg's linker figures are `estimated` and said to be so; no timing figure appears anywhere, because no benchmark exists yet. |
| **V. Budgets Are Gates, Not Warnings** | The site explains the gate as a gate: leg 4 is a failing budget read and acted on, and FR-023 requires the gate and the fit check to be explained as concepts. No page offers a way to soften or skip one, because none exists. |
| **VIII. No Lock-In: Portable Artifacts, Local Execution** | The site builds and reads offline with no accounts (FR-051, SC-015). The deployment leg documents a model running on a board through that board's own open toolchain, which is the principle's own claim made legible. |
| **XII. Small Core, Few Dependencies** | No runtime dependency and no extra is added. The theme is templates and static files, so it installs nothing. The browser audit goes in a pinned dependency group — see the dependency gate below. |
| **Project Scope & Relationship to the Zoo** | *"Caravan MUST NOT depend on the zoo."* The identity is a copy: no shared package, no submodule, nothing fetched at build time (FR-028). Licences permit it — both repositories are Apache-2.0 with the same owner, the typefaces are OFL-1.1 and the notice travels with them. The two identities may drift, and the design language says so. |
| **Target Hardware & the Verification Ladder** | The firmware build verifies that the exported C and the firmware compile; it does not claim to run them. That is `estimated`, and the workflow already says so. A board run stays the owner's, on the rung above. |
| **Resources & Cost Discipline** | One pull request for the feature, opened when the implementation is built and locally validated. The site's checks run in the documentation workflow rather than the framework matrix, which constitution 4.2.0 now permits explicitly and bounds at one job, one Python version, no extras and ten minutes. FR-050 carries the bound and T088 measures it. |
| **Development Workflow & Quality Gates** | This plan lists the principles it touches, as required, and is re-checked after design. No stage of the pipeline changes, so the stage gate does not apply; the layering test and the install budget are untouched and still run. |
| **XI. No Claude in Model Learning or Extraction** | Nothing in this feature labels, generates or evaluates data, and no model is trained by it beyond the existing example run. Admits no deviation and needs none. |

**Dependency gate** (required before adding any dependency, Development Workflow). The constitution asks these of *the spec*, and spec.md now carries them under "A dependency this feature adds"; they are repeated here because the plan is where the choice is acted on:

- *What it replaces*: nothing today. SC-012 requires the accessibility claim to be measured in a
  browser on the rendered page, and the site has no such check — the claim is currently unmeasured.
- *Why it cannot be owned in a few hundred lines*: the audit is a standing ruleset for the A and AA
  levels, maintained against the specifications and the browsers. Writing it would mean owning an
  accessibility standard; computing contrast from the tokens instead is what SC-012 refuses,
  because it cannot see text over an image or a focus ring.
- *Which extra it belongs to*: **none.** It is a pinned dependency group used to check the site,
  never installed with the package, exactly as the `docs` group is. The distribution's dependency
  count and extras are unchanged, so the budget of Principle XII is unaffected.
- *That the budget holds*: the cold-install budget measures the default distribution, which this
  does not touch; the install-budget job proves it unchanged.
- *That it does not constrain the Python policy*: the group is only ever resolved on the site's own
  Python (3.13) in one job. It is never resolved with the package, so it cannot narrow the
  published window.

**Gate verdict before Phase 0: pass**, with one documented tension (below) and no principle
deviation.

## Project Structure

### Documentation (this feature)

```text
specs/010-website-overhaul/
├── plan.md              # This file
├── research.md          # Phase 0: the eight unknowns, settled
├── data-model.md        # Phase 1: the content model
├── quickstart.md        # Phase 1: how to validate the feature
├── contracts/
│   ├── page-inventory.md   # Every address, what it becomes, what forwards
│   ├── design-tokens.md    # The identity's contract, and what the accent is for
│   └── checks.md           # What each check asserts and where it runs
├── checklists/
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks.md             # Created by /speckit-tasks, not here
```

### Source Code (repository root)

```text
docs/
├── conf.py                      # theme path, redirect map, front-matter layouts
├── index.md                     # the landing page (three-second verdict)
├── route/                       # the series; "leg" is the reader's word for a part
│   ├── index.md                 # what the route is and what each leg ends with
│   ├── 1-first-model.md         # ~5 min  → an int8 model and its C array exist
│   ├── 2-your-columns.md        # ~15 min → a model reading the reader's own data
│   ├── 3-onto-a-board.md        # ~30 min → an ESP32 answering, checked against the host
│   └── 4-when-it-does-not-fit.md# beyond  → a failing gate read and a budget chosen
├── concepts/                    # one idea per page, linked from route and reference
│   ├── templates.md             # what "MLP" and "conv1d" are, and which to pick
│   ├── feature-types.md         # number, category, binary, and their preprocessing
│   ├── budgets-and-gates.md     # the int8 gate and the fit check, as concepts
│   └── what-a-run-leaves.md     # the artifacts, explained where they are first met
├── reference/                   # lookup kept, rule codes demoted to prose
│   ├── cli.md
│   ├── manifest.md
│   └── rules.md
├── compatibility.md
├── roadmap.md
├── _themes/caravan/             # the identity, copied; adds nothing to install
│   ├── theme.conf
│   ├── layout.html              # from the zoo's base template
│   ├── landing.html             # the one page that is not an article
│   └── static/
│       ├── tokens.css           # copied verbatim
│       ├── site.css             # copied, selectors mapped to Sphinx's body markup
│       ├── fonts/               # two typefaces, OFL-1.1, with their notice
│       └── img/mark.svg         # Caravan's own mark, not the zoo's
└── _ext/redirects.py            # writes a forwarding stub per moved address

examples/esp32/                  # the deployment leg's firmware, generic and serial-only
├── platformio.ini               # esp32dev
├── sdkconfig.defaults
├── CMakeLists.txt
└── src/{main.cc,CMakeLists.txt,idf_component.yml,model/README.md}

examples/lora32/                 # unchanged: the owner's own board (D2), off the site

tests/
├── contract/test_docs_reference.py   # extended: every setting has its prose
├── contract/test_docs_guide.py       # extended: the legs' version strings
├── contract/test_docs_glossary.py    # new: no unexplained abbreviation
├── contract/test_docs_hygiene.py     # new: no board, no internal artifacts, no dead address
├── site/test_a11y.py                 # new: the browser audit, both schemes
└── train/test_route_legs.py          # renamed from test_try_it_guide.py

.github/workflows/
├── docs-checks.yml              # extended: the audit joins the page checks
└── firmware.yml                 # extended: the generic project and the leg's blocks
```

**Structure Decision**: the site keeps its home in `docs/` and Sphinx keeps building it, so the
existing checks — warnings as errors, no orphan page, no broken anchor — stay the floor rather than
being rebuilt (R1, R8). Three directories are new and each answers one requirement: `route/` is the
series FR-007 asks for, `concepts/` is where FR-024 puts an explanation that both the route and the
reference link to without duplicating it, and `_themes/caravan/` is the copied identity that
FR-028 requires to be a copy. The firmware lives beside the example that already exists rather than
replacing it, because D2 keeps that one.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(resolved — kept for the record)* A documentation-only change starts a job, which the constitution forbade when this plan was written | The site's claims have to be checked somewhere: the pages against the code, the build against broken links, the pages against the accessibility level SC-012 states. Before this feature those checks either rode the full framework matrix — nine jobs for a comma in the README — or did not exist. | The owner amended the constitution to 4.2.0 on 2026-10-27 rather than have the plan dilute the rule. The prohibition now sits where the cost is, on the framework matrix, and spec/plan/tasks commits still start nothing; published documentation may start one job, bounded at one job, one Python version, no extras and ten minutes, with a job that outgrows the bound losing checks rather than gaining time. No deviation remains. |
| `main.cc` exists twice — once for the generic board, once for the owner's | D2 keeps `examples/lora32/`, so the generic path cannot be made by converting it, and FR-039 forbids sending a reader into a directory whose configuration names the withdrawn board | *One project with two PlatformIO environments* was rejected for that second reason. The duplication's risk is drift, and the mitigation is that continuous integration builds both, so drift fails a check rather than rotting quietly. |

## Post-design re-check

Re-verified after Phase 1, as the Development Workflow requires.

- **Nothing in the design adds a runtime dependency or an extra.** The theme installs nothing; the
  audit is a group. The install budget and layering jobs are untouched and still gate the merge.
- **Nothing in the design reaches the zoo at build time.** `contracts/design-tokens.md` fixes the
  identity as copied values with their origin recorded, which is what makes FR-028 checkable.
- **No unlabeled hardware figure is introduced.** `contracts/checks.md` makes the provenance label a
  check rather than a habit: a figure about a board that carries no label fails the site's checks.
- **No page gains a way to soften a gate**, and leg 4 teaches the gate by failing it on purpose.
- **The one tension that stood is resolved**, by constitution 4.2.0 rather than by reinterpreting the rule. The bound it introduces is a new obligation on this feature, carried by FR-050 and measured by T088.

**Gate verdict after Phase 1: pass.**
