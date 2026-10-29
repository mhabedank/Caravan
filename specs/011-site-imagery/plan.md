# Implementation Plan: Imagery for the site

**Branch**: `011-site-imagery` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-site-imagery/spec.md`

## Summary

Generate the site's pictures instead of fetching them, with the zoo's method copied rather than
imported: a series file as the art direction, a generator in a CUDA container, two local pages to
decide from, and a placement command that brings a picked image in as a record directory.

The draft on this branch already covers stories 1–3. What this plan adds is story 4 — the part the
draft deliberately left out — and the five decisions the clarification session settled: the
hand-drawn SVGs are replaced, the site is gated at 3 MB, placement is zoo-shaped, disclosure runs
through the zoo's four channels, and the images go out under CC0-1.0.

The port is small because only a fraction of the zoo's 1,609 lines is wanted. Records, derivatives,
the XMP marker and the credits page need **Pillow and nothing else**; the triage half (opencv,
onnxruntime, rapidocr, a fetched YuNet model) stays out, which is what keeps FR-008 true.

## Technical Context

**Language/Version**: Python 3.13 for the three scripts (PEP 723, run with `uv run --script`);
Sphinx 9.2.0 with myst-parser 5.1.0 (pinned in the `docs` dependency group) for the site.

**Primary Dependencies**: none added to the distribution. The scripts declare their own:
`pyyaml>=6` and `pillow>=11`. The container adds `diffusers`, `transformers`, `accelerate`,
`sentencepiece`, `protobuf`, `huggingface_hub` on top of `nvcr.io/nvidia/pytorch:25.09-py3`.

**Storage**: plain files. Rounds stay on the owner's machine (never committed); placed records live
in the repository at `docs/_static/images/<id>/`.

**Testing**: no new test suite — feature 010's D5 removed the website's checks on purpose. What
verifies this feature: the placement command's own refusals, the site build with every warning an
error, and one measured weight gate (FR-029).

**Target Platform**: rendering on a CUDA machine (written for the DGX Spark: arm64, CUDA 13) inside
the container; the pages, the placement command and the site build on an ordinary dev machine.
Output is static HTML.

**Project Type**: documentation-site assets plus three standalone scripts, all outside the
distribution.

**Performance Goals**: a full round of ~80 candidates unattended in about four hours; the subject
page builds in under a second from the series file alone; the contact sheet stays usable with 80
thumbnails; the documentation CI job stays inside its ten minutes (SC-007).

**Constraints**: `pyproject.toml` byte-identical (FR-008); no network but the model host and no
credentials (FR-011); the served site under 3,000,000 bytes (FR-029); the site build invokes none
of this (FR-010).

**Scale/Scope**: 20 subjects — 19 with a placement, 1 held in reserve — at 4 seeds a round, so ~80
candidates; 19 placed records × 3 derivatives = 57 WebP files.

## Constitution Check

*GATE: verified before Phase 0 and again after Phase 1 design. Both passes recorded below.*

| Principle | Verdict | How this feature complies |
|---|---|---|
| III. Reproducible by Construction | PASS, with a documented deviation | Seeds are derived from the subject key and recorded per image; the manifest carries the full recipe (FR-018). Byte-identical reproduction holds only on the same hardware — the deviation Principle III requires to be documented, and the manifest records the hardware class so the limit is visible rather than implied. |
| IV. Measured, Emulated or Estimated | PASS | No number about model behaviour on hardware is produced here. The one figure this feature does report — the site's weight — is measured on the built output, never asserted. The disclosure requirements (FR-032–034) are the same principle applied to a picture: what produced it travels with it. |
| V. Budgets Are Gates, Not Warnings | PASS | FR-029 states a figure, measures it on the built output, exits non-zero when it is exceeded, and cannot be raised by a flag or an environment variable. The threshold is committed, not passed in. |
| VIII. No Lock-In, Local Execution | PASS | Local GPU, no account, no token, no hosted service. Model weights come from a one-time local Hugging Face cache; that is not a stage of building a model. |
| XI. No Claude in Model Learning or Extraction | PASS, no deviation sought | The images are produced by FLUX.2-klein-4B and Qwen-Image-2512 — no Claude model anywhere in the path — and they are site decoration that never becomes model input data. The manifest records the producing model per image, so a Claude model would be visible and would fail the gate. Claude's use here is as a development assistant on spec, plan and code, which Principle XI expressly permits. |
| XII. Small Core, Few Dependencies | PASS | `pyproject.toml` is unchanged: no runtime dependency, no extra, no dependency group. The scripts carry their dependencies inline. Porting ~250 readable lines instead of depending on the zoo is exactly the rule "code the project could own in a few hundred readable lines MUST NOT become a dependency". The Pillow-only port keeps opencv, onnxruntime and rapidocr out. |
| Project Scope & the Zoo | PASS | Copied, not shared: nothing imports the zoo, fetches from it or requires it installed, and the copied files say where they came from and that the two may drift. No zoo model code, dataset or credential is carried, and the subjects are Caravan's own (FR-003). |
| Resources & Cost Discipline | PASS | Local compute, the first tier the constitution asks for, at no cash cost — so no cash budget is required. No credential is read, written or needed. The documentation job stays one job, one Python, no extras, inside ten minutes. |
| Development Workflow & Quality Gates | PASS | No dependency or extra is added, so that gate does not apply. Both artifacts list the principles they touch, as required: this table, and the spec's own "Principles this touches" section added after the cross-artifact analysis. |

**Post-design re-check (after Phase 1)**: unchanged. The design adds one `place.py` script with two
inline dependencies, 19 record directories and one generated page; it adds no distribution
dependency, no extra, no CI job and no hosted service. The two tensions it does create are tracked
below rather than waved through.

## Project Structure

### Documentation (this feature)

```text
specs/011-site-imagery/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── cli.md                     # the three commands
│   ├── image-record.schema.json   # the placed record
│   └── weight-gate.md             # how the 3 MB is measured
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
scripts/imagery/                  # nothing here is part of the distribution
├── Dockerfile                    # exists — the CUDA container
├── README.md                     # exists — extend with placement and the licence note
├── gen.py                        # exists — renders a round, writes manifest.json
├── sheet.py                      # exists — the subject page and the contact sheet
├── place.py                      # NEW — picks.yaml + manifest.json -> record directories
├── .gitignore                    # NEW — keeps generated pages and rounds out of the repository
└── series/
    └── siebdruck.yaml            # exists — 20 subjects, 19 placed + 1 reserve

docs/
├── _static/images/<id>/          # NEW — one directory per placed image
│   ├── <id>-480.webp             #   three derivatives, XMP-marked
│   ├── <id>-960.webp
│   ├── <id>-1600.webp
│   └── image.yaml                #   the record: recipe, licence, alt, placements
├── credits.md                    # NEW — written by place.py from the records
├── conf.py                       # add html_static_path = ["_static"]
└── _themes/caravan/
    ├── layout.html               # add the footer credits link (FR-034)
    └── static/img/               # hero.svg + leg-1..4.svg retired as replacements land;
                                  #   favicon.svg and mark.svg are brand marks and stay

.github/workflows/docs-checks.yml # add the weight gate step (FR-029)
NOTICE                            # add the model licences and the images' CC0-1.0 (FR-030)
```

**Structure Decision**: the scripts stay in `scripts/imagery/`, where the draft already put them
and where the site build cannot reach them. Placed records go under `docs/_static/images/`, which
Sphinx copies verbatim into `_build/html/_static/images/` with no build logic of ours — the cheapest
way to satisfy FR-010 while keeping each image's record beside the image it describes, so FR-020's
traceability is a published fact rather than a repository convention.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| The documentation CI job gains one step, the weight measurement | Principle V forbids a budget that nothing measures, and an unmeasured ceiling is the thing the owner asked for a gate against. The step sums the bytes of the built output: milliseconds, no new dependency, no browser. FR-010 was amended after analysis to permit exactly this one measurement and nothing else, so the spec no longer forbids what FR-029 requires. | Asserting the weight in prose was rejected by Principle V ("a stage that cannot determine whether a budget holds MUST fail"). Measuring it outside CI was rejected because a gate nobody runs is not a gate. SC-007's ten minutes remains the bound that actually governs, and this step is immeasurable against it. |
| The credits page returns after FR-007 had excluded it | The clarification chose the zoo's disclosure exactly, and the credits page is the surface the footer link points at; without it FR-034 has no target. | Alt text alone was offered as the recommendation and declined. The page is written by `place.py` from the records and committed, not generated by the site build, so FR-010 still holds. |
