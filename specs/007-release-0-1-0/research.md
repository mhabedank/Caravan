# Research: Release 0.1.0

All figures measured on 2026-10-23 on `main` at `8c917e1`, Python 3.13.16, TensorFlow 2.21.0,
Keras 3.15.1, unless stated otherwise.

## R1. Where the console noise comes from, and how to keep it

**Measured.** `caravan export` on `picket-mlp-fixture.yaml`, stdout and stderr captured apart:

| Stream | Lines | Source |
|---|---|---|
| stdout | 26 | Keras's `model.export()` printing "Saved artifact at …", the endpoint signature and one `TensorSpec` line per captured variable — twice, once per conversion |
| stderr | 44, of which 9 are Caravan's | TensorFlow's C++ logging (absl: oneDNN, CUDA probing, `cuInit` failure, SavedModel loader, MLIR passes), a Python `UserWarning` from the converter, the converter's `fully_quantize: 0 …` line, and the XNNPACK delegate notice |

Two consequences beyond looks:

- **`--json` output is corrupted today.** The Keras listing goes to stdout, where the stage verbs
  write their JSON document with `--json`. A pipe into a JSON reader fails on the first line.
  That makes the noise a defect, not only a cosmetic one.
- **Part of it is not Python.** The absl lines are written by C++ directly to file descriptor 2,
  so neither `contextlib.redirect_stdout` nor the `logging` or `warnings` modules reach them.

**Decision.** While stages run, the pipeline redirects file descriptors 1 and 2 to a file in the run
directory, `framework.log`, and restores them afterwards (`os.dup` / `os.dup2`, Python standard
library, no dependency). Caravan prints nothing during stages — its summary and findings come after
the stage loop — so nothing of its own is captured. On a failure inside a stage, the descriptors are
restored before the failure is reported, and the message names `framework.log`. A switch on the
stage verbs, `--framework-output`, skips the redirection.

The redirect wraps the whole stage loop, including the first import of the training framework,
because the oneDNN and CUDA lines are printed at import time.

**Alternatives considered.**
- *`TF_CPP_MIN_LOG_LEVEL=3` and `absl.logging` levels.* Rejected as the mechanism: they silence
  rather than keep, so a framework crash loses its cause (spec, US2 scenario 2), they do not cover
  the Keras `print`, and they depend on the framework's own variable names, which have changed
  before. Setting nothing in the environment also keeps runs comparable.
- *`contextlib.redirect_stdout` and `redirect_stderr`.* Rejected: they swap Python's `sys.stdout`
  objects only, and the absl lines bypass Python.
- *Running stages in a subprocess.* Rejected: a large change to how stages run, for the same effect.

## R2. How a tagged version is installed without the package index

**Decision.** The release workflow builds the wheel and the sdist from the tag, checks them and
attaches them to a GitHub release of that tag. The guide installs the wheel by its release URL:

```text
pip install "caravan-ml[train,verify] @ https://github.com/mhabedank/Caravan/releases/download/v0.1.0rc1/caravan_ml-0.1.0rc1-py3-none-any.whl"
```

The README also shows the `git+https://…@v0.1.0rc1` form for authors who prefer to build from the
source themselves.

**Rationale.** The wheel attached to the release is the file CI checked, which is what FR-003 asks
for: the package tested is the package installed. A `git+` install builds again on the author's
machine, from the same tag but not from the same file, and needs `git`.

**Alternatives considered.** *The package index* — ruled out by the owner for this release
(2026-10-23). *Only `git+`* — kept as the second form, not the first, for the reason above.

## R3. The version number and the tag

**Measured.** The version is written in two places, `pyproject.toml` (`version = "0.1.0.dev1"`) and
`src/caravan/__init__.py` (`__version__ = "0.1.0.dev1"`). Run reports and cache keys carry
`__version__`.

**Decision.** Both are set by hand for each tag, in one commit, and two checks hold them together:

- a unit test asserts that `__version__` equals the version in the installed distribution's
  metadata, so the two cannot drift on `main`;
- the release workflow asserts that the built package's version equals the tag, normalised the way
  packaging normalises it (`v0.1.0rc1` → `0.1.0rc1`), and fails before anything is published
  otherwise.

The candidates are `0.1.0rc1`, `0.1.0rc2` and so on, which PEP 440 orders before `0.1.0`.

**Alternatives considered.** *A version derived from the tag at build time* (hatch-vcs). Rejected:
a new build dependency for two lines edited once per release, and a version that differs between a
checkout and a build is harder to explain than one written down.

## R4. The guide's example, from an installed package

**Measured.** The one committed dataset is `tests/fixtures/datasets/synthetic/records.csv`,
113,616 bytes, with its generator `make.py` beside it. The constitution allows this tiny synthetic
fixture and nothing else.

**Decision.** A new directory `examples/` holds `picket-mlp.yaml`: the pilot manifest, identical to
`tests/fixtures/manifests/valid/picket-mlp-fixture.yaml` apart from its comments and its
`dataset.source`, which points at the committed fixture by a path relative to the example. A test
asserts that the two manifests agree field for field, so the example cannot drift from what the
suite runs. The guide fetches only those two directories from the tag's source archive with one
command:

```text
curl -sL https://github.com/mhabedank/Caravan/archive/refs/tags/v0.1.0rc1.tar.gz \
  | tar xz --strip-components=1 Caravan-0.1.0rc1/examples Caravan-0.1.0rc1/tests/fixtures/datasets/synthetic
```

No data is duplicated, no `git` is needed, and the result is about 120 kB.

**Rationale.** FR-006 asks for a guide that works from an installed package. The package itself
should not carry a dataset (the core stays small, and Principle XII fixes the verb set, so there is
no `caravan example` to unpack one). Downloading two directories of the tagged source is the
smallest step that needs no checkout, no development tooling and no copy of the data.

**Alternatives considered.**
- *Shipping the CSV inside the wheel.* Rejected: no verb could unpack it, and a hidden module entry
  point would be a verb by another name.
- *A second copy of the data under `examples/`.* Rejected: two copies of the one allowed dataset,
  and the regeneration test would have to cover both.
- *Moving the fixture to `examples/`.* Rejected for this release: it touches twenty references in
  the tests for no gain to the author.
- *A full `git clone`.* Rejected: the spec asks for no checkout.

**Limit, stated.** The command assumes `curl` and `tar` (Linux, macOS). Windows is not a stated
platform of 0.1.0.

## R5. Testing what the documents say (SC-003)

**Decision.** The guide, `docs/try-it.md`, marks its command blocks as `fetch`, `install` or `run`.
A test reads the blocks from the file and executes the `run` blocks, unchanged, in a temporary
directory prepared like the `fetch` block would prepare it (copies of `examples/` and the dataset
from the working tree), with the `caravan` on the test environment's path. It asserts every exit
code, that the run directory holds the listed files, and SC-002: the `export` step's console output
is at most 25 lines and carries none of the framework's lines (R1's list). It lives in `tests/train`,
because the `run` block trains.

The release workflow then runs the guide literally, `fetch` and `install` included, against the
release it has just published. That is the only place where the published wheel URL and archive URL
exist.

The README's commands are checked by the same mechanism: its quick-start block runs in the clean
environment job (validate and render only), its install lines are compared against the guide's.

**Alternatives considered.** *Reading the documents by hand before each release.* Rejected:
SC-003 asks for a test, and the README of 0.1.0.dev1 shows that reading did not catch a broken
install line.

## R6. The release workflow

**Decision.** `.github/workflows/release.yml`, on a pushed tag `v*`:

1. **check** — the tag's version equals the package version (R3); the whole suite on 3.13 with both
   extras; the guide test.
2. **build** — `uv build` from the tag; install the wheel into a clean 3.13 environment with both
   extras and into a clean 3.14 environment without; `caravan --version` must print the tag's
   version in both.
3. **release** — create the GitHub release for the tag with the release note as its body, attach
   the wheel and the sdist, and mark it a pre-release when the version is a candidate. Uses the
   workflow's own `GITHUB_TOKEN` with `contents: write`; no other credential exists.
4. **verify** — on a fresh runner, run the guide literally against the published release (R5).

A failure in steps 1 or 2 publishes nothing. A failure in step 4 leaves a published release that is
broken; the procedure (contract `release.md`) then marks it as such in its notes and tags the next
candidate, because a tag is never moved.

**Alternatives considered.** *Creating releases by hand.* Rejected: the check that the package
matches the tag would then depend on remembering it.

## R7. What the release gate of the constitution asks, concretely

The Development Workflow's gate before a framework release: semantic versioning; a change note for
every breaking schema change; the pilot manifest green. For 0.1.0:

- **Semantic versioning.** `0.1.0rc1` → `0.1.0` is PEP 440 and semver-compatible in meaning; the
  first public version needs no compatibility statement (constitution 4.0.0: none before 1.0.0).
- **Change note.** There is one breaking schema change since development began, `caravan/v0` →
  `caravan/v0.1`, and its note is in `docs/manifest-changes.md`. The release note links it.
- **Pilot manifest green.** The `train` job runs the pilot end to end on every push; the release
  workflow runs it again from the tag (R6, step 1).

The gate is recorded in the release note as a checklist with the workflow run that proved each item.

## R8. The `pace-cnn` port

*Filled in from the investigation of the zoo; see below.*
