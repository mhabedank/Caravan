# Phase 0 Research: Build and Train

Date: 2026-10-22 · Feature: 002 · Input: [spec.md](./spec.md)

Every external claim below was checked against the live package index on 2026-10-22 and the
command that checked it is named, because the whole feature turns on which wheels exist.

## R1 — The training framework, and the Python window it forces

**Decision**: Keras/TensorFlow, stable `tensorflow>=2.21,<2.22` with `keras>=3.12`, carried by the
`train` extra and installed only on Python 3.13. The published distribution's floor moves from
`>=3.14` to `>=3.13`, and 3.13, 3.14 and 3.15 are all tested. On 3.14 and 3.15 the extra installs
Caravan's own training code but no framework, and `build` and `train` then fail with the message in
R2.

**Evidence**:

| Checked | Result |
|---|---|
| `tensorflow` 2.21.0 (stable) wheel tags | `cp310 cp311 cp312 cp313` — nothing for 3.14 or 3.15 |
| `tensorflow` 2.22.0rc0 wheel tags | `cp310 … cp313 cp314` — a 3.14 wheel exists |
| 2.22.0rc0's dependencies | requires `keras-nightly>=3.12.0.dev`, where 2.21.0 requires `keras>=3.12.0` |
| `uv pip install --python 3.14 --prerelease=explicit "tensorflow>=2.22.0rc0"` | no solution: `keras-nightly` needs pre-releases enabled globally |
| `uv pip install --python 3.14 --prerelease=allow "tensorflow>=2.22.0rc0"` | resolves — and pulls `keras-nightly`, `grpcio==1.85.0rc1`, `protobuf==7.37.0rc1`, `wrapt==2.5.2rc1` |
| `uv pip install --python 3.13 "tensorflow>=2.21,<2.22"` | resolves, 32 packages, every one of them a stable release |
| `jaxlib` 0.12.0.1 wheel tags | `cp312 cp313 cp314 cp315` |
| `torch` 2.14.1 wheel tags | `cp310 … cp314` |
| `ai-edge-litert` 2.3.0 wheel tags | `cp310 … cp314` |

**Rationale**: the shape of the problem is not "TensorFlow has no 3.14 wheel" — it has one, in a
release candidate. It is that the release candidate depends on a *nightly* build of Keras. A
published distribution cannot declare that dependency: it resolves only when the installing user
enables pre-releases for every package in the graph, which on 3.14 today also means release
candidates of grpcio, protobuf and wrapt. Shipping that as the supported way to train would be
exactly the dependency weight this project exists to avoid. On 3.13, by contrast, the entire
32-package graph is stable.

The constitution's own Python policy requires the current and previous stable minor to be
supported; it does not forbid supporting one more. Lowering the floor to 3.13 therefore keeps the
policy's substance as long as 3.13 is genuinely tested, which is why that is now a condition in
Principle XII rather than a remark here (constitution v2.3.0, amended during this phase — the gate
failed on it, see plan.md).

**Alternatives considered**:

- **Keep the floor at 3.14 and declare the extra anyway.** Mechanically impossible, and this is
  what v2.2.0 of the constitution assumed was possible: `requires-python` is distribution-level
  metadata, there is no per-extra window, so `pip install caravan-ml[train]` fails on 3.13 (the
  distribution refuses the interpreter) and on 3.14 (the framework has no wheel). The extra could
  not be installed on any interpreter at all. Rejected because it does not exist.
- **A second distribution, `caravan-train`, with its own `requires-python`.** It would have to
  depend on `caravan-ml`, which on 3.13 refuses to install. Same wall, one package later.
- **Depend on the release candidate.** Rejected: `keras-nightly` is not a dependency a published
  project may carry, and a nightly's content changes under the same version string, which breaks
  the provenance record Principle III requires.
- **Keras 3 on a JAX backend**, which installs cleanly on 3.14 *and* 3.15. Rejected for now, and
  the reason is not training: it is that the next feature must convert to int8 TFLite, and that
  converter lives in TensorFlow. Training on JAX and converting on TensorFlow means two frameworks
  and a handoff between them, in a project whose central rule is to have few. The Technical
  Baseline records that this reopens at the quantize stage, where `ai-edge-litert`'s cp314 wheel is
  the thing to investigate.
- **Install with `--ignore-requires-python` in continuous integration and ship the floor at 3.14
  anyway.** Rejected: it would make the test suite pass on an installation no user can reproduce,
  which is worse than an honest floor.

**The obligation this creates**, recorded here, in `docs/budgets.md` and in the roadmap: when a
stable TensorFlow ships a cp314 wheel depending on a released `keras`, the extra moves to it, the
floor returns to 3.14, and the 3.13 job is deleted.

## R2 — Detecting the extra's absence, and saying something useful

**Decision**: a single core module, `caravan/env.py`, answers one question — is the training
framework importable — and renders one of two messages. Exit code **4**, "the environment is
incomplete", distinct from 1 (a rule said no) and 3 (a defect in the tool).

- On Python 3.13, framework absent: *name the install command*.
  `the train extra is not installed — install it with: pip install "caravan-ml[train]"`
- On Python 3.14 or newer, framework absent: *name the window and the reason*, because the user may
  have just run that install command and received nothing.
  `training needs TensorFlow, which publishes no wheel for Python 3.14 (checked 2026-10-22: 2.21.0
  ships cp310 through cp313). Train on Python 3.13; the rest of Caravan runs here.`

**Rationale**: FR-020 asks for an actionable message rather than a traceback. The second case is
the one that would otherwise be unactionable: with the markers from R1, `pip install
caravan-ml[train]` on 3.14 succeeds and installs no framework, so a message that only repeats the
install command would send the user in a circle. The check is `importlib.util.find_spec`, not an
import, so the core never loads the framework to discover that it exists — which keeps the layering
test of feature 001 meaningful.

**Alternatives considered**: letting the import error surface (rejected: FR-020 forbids it); exit
code 1 (rejected: a missing framework is not a broken rule, and continuous integration must be able
to tell them apart); no marker on the extra's dependency, so `pip` itself refuses on 3.14 (rejected:
a resolver error naming `tensorflow>=2.21` does not tell a user that 3.13 is the answer, and
condition 4 of Principle XII now forbids it).

## R3 — Where the builder half lives, and how it stays unimported

**Decision**: `caravan/templates/builders/<identifier>.py`, next to the parameter half, imported by
name only when a stage asks for it — `importlib.import_module(f"caravan.templates.builders.{id}")`
— plus the entry point group `caravan.template_builders` for third parties. The core's built-in
discovery walk in `templates/registry.py` gains one line: it skips subpackages, because a parameter
spec is always a module and `builders` is a package.

**Rationale**: the two halves of a template belong next to each other — the alternative puts the
`mlp` parameters and the `mlp` builder in directories that do not look related, which is how the
halves drift apart. Keeping them adjacent costs exactly one condition in the discovery walk, and a
layering test proves the consequence that matters: building the template registry imports no
framework.

**Alternatives considered**: `caravan/train/builders/` (rejected: splits a template in two places);
registering builders in a central list (rejected by FR-021 — adding a template must not edit a
central list); a `TemplateBuilderSpec` dataclass mirroring the parameter spec (deferred: one
callable with a documented signature is enough for one template, and a second template is what
should force the abstraction).

## R4 — The dataset reader lives in the extra; the dataset *version* lives in the core

**Decision**: two different things, deliberately in two places.

- **Version** (`caravan/data/fingerprint.py`, core, standard library only): a SHA-256 over, for
  each file in sorted relative-path order, the path, the byte length and the file's bytes. No
  parsing. This is what the cache key uses and what the report records.
- **Reader** (`caravan/data/reader.py`, extra only, imports `numpy`): the only code that parses the
  data into arrays, applies the windowing rule of R5 and produces the split of R6.

**Rationale**: the cache has to answer "did the dataset change" without a training framework
installed, and a content hash answers it honestly — mtime and size do not. Parsing, by contrast,
only ever happens inside a stage that already needs the framework, so there is no reason for the
core to carry a reader, and every reason not to: a second reader in the core would be a second
implementation of the windowing rule to keep in step with the first.

**Cost, stated**: hashing the author's real dataset reads every byte on every run — roughly a
second per gigabyte, once per run. Accepted; the alternative is a cache that can be wrong.

**Alternatives considered**: a stdlib `csv` reader in the core with a fast `numpy` path in the extra
(rejected: two implementations of one rule, the kind of duplication Principle XII warns about);
size and mtime as the version (rejected: silently wrong after a touch or a rewrite in place);
`pandas` (rejected: a large dependency for `genfromtxt`).

## R5 — Windowing, and the window whose records disagree

**Decision**: records are read in sequence order (file order; across files, sorted relative path).
A sample is `dataset.window` consecutive records, windows do not overlap, and a trailing remainder
shorter than a window is dropped and counted. A window whose records do not all carry the same
label is **discarded** and counted. With no `window` in the manifest, one record is one sample.
Both counts — kept, discarded for label disagreement, dropped as a remainder — go into the run
report (FR-025).

**Rationale**: non-overlapping windows are the only choice under which a random split does not leak
— two overlapping windows share records, so one can land in train and the other in test and the
test score stops meaning anything. Discarding a mixed window is the honest alternative to inventing
its label: majority voting has no answer for a tie, and "the last record's label" silently
mislabels the tail of every attack burst.

**Alternatives considered**: overlapping windows with a stride (rejected for the leak; a stride
field can arrive when a model needs one, with a split that respects it); majority label (rejected:
ties); last record's label (rejected: systematic mislabelling at boundaries); keeping mixed windows
with a "mixed" label (rejected: invents a class the manifest does not declare).

## R6 — The split is over samples, stratified, and seeded

**Decision**: the split applies to **windows**, not records, after the discard of R5. Procedure,
specified because it has to be reproducible: group sample indices by label; sort each group
ascending; shuffle each group with `random.Random(seed)` seeded from `train.seed`; take the first
`train`, then `val`, then `test` fraction of each group by `math.floor`, and hand the remainder of
each group to the split with the largest fraction, ties going to `train`. With
`stratified: false`, the same procedure runs once over all indices instead of per label.

A split part that comes out empty is a failure naming the part, the label and the counts — the
manifest already forbids a zero fraction (rule CF-1), so an empty part means the data is too small
for the manifest, which is the author's to fix.

**Rationale**: stratifying over records rather than windows would be meaningless once records are
grouped into windows. Writing the procedure down, including the remainder rule, is what makes two
runs comparable; "shuffle and slice" is not reproducible across implementations of the same
sentence. The standard library's `Random` is used rather than the framework's, so the split does not
depend on which framework is installed.

**Alternatives considered**: a chronological split (defensible for time series, and arguably more
honest for intrusion detection — recorded here as the thing to reconsider when `pace-cnn` arrives,
since it changes what the metrics mean); the framework's own splitting utilities (rejected: ties the
split to the framework and makes it unreproducible from the report alone).

## R7 — The cache key, and making "the fields the stage reads" true by construction

**Decision**: each stage declares `READS`, a tuple of dotted paths into the resolved manifest, and
the stage runner hands the stage **only a projection** built from exactly those paths. A stage
cannot read a field it did not declare, because it never receives one.

The key is `sha256` over canonical JSON (`sort_keys=True`, `separators=(",", ":")`) of:

```json
{"tool": "0.1.0.dev1", "schema": "caravan/v0", "stage": "train",
 "inputs": {"<declared path>": "<value>", "...": "..."},
 "dataset": "<dataset version, when the stage reads the dataset>",
 "upstream": "<the key of the stage before it, when there is one>"}
```

The test that makes FR-014 and FR-015 real is generic rather than a list of cases: it walks every
leaf path of the pilot manifest, changes it, and asserts the key moves if and only if the path is in
the stage's declared set. Adding a field to the schema cannot quietly escape it.

**Rationale**: declaring what a stage reads and then reading something else is the failure mode that
makes caches wrong, and no amount of review catches it reliably. A projection makes the declaration
the only access path. The tool version is in the key on purpose: a different tool may produce a
different model, and Principle III makes provenance part of the result. It costs a full retrain
after a version bump, which is correct and cheap at this size.

**Alternatives considered**: hashing the whole resolved manifest (rejected: editing compliance text
would retrain, which is the specific thing FR-015 forbids); inferring the read set by tracing
attribute access (rejected: clever, fragile, and untestable); leaving the tool version out
(rejected: dishonest — the artifact would claim to be reusable across tool versions that may not
produce the same model).

## R8 — The cache store, and what reuse puts in the run directory

**Decision**: `./.caravan/cache/<stage>/<key>/` holds the stage's artifacts and a `result.json`
recording the key's inputs, the run that produced them and the time. `--cache-dir` moves it;
`--fresh` bypasses it for this run and is recorded in the report (FR-017). On reuse the artifacts
are **copied** into the new run directory, and the report records `reused: true`, the key, and the
run that originally produced them. A cache entry whose artifacts are missing or unreadable is
treated as absent and the stage runs (FR-018).

**Rationale**: every run directory should be complete on its own — a run report that points at a
cache entry stops being readable the moment the cache is cleaned, and these artifacts are kilobytes.
`.caravan/` sits beside `runs/` so a clean is one `rm -rf`, and both go in `.gitignore`.

**Alternatives considered**: hard links (rejected: a later run could mutate a cached artifact through
its link); a pointer in the report (rejected: makes a run directory depend on a cache); caching
inside `runs/` (rejected: a run directory is per invocation by the contract of feature 001).

## R9 — What this feature promises about reproducibility, exactly

**Decision**: `keras.utils.set_random_seed(seed)` before building and before training, the seed and
every effective setting recorded (FR-008), and **no** claim of bit-identical weights. TensorFlow's
op determinism (`enable_op_determinism`) is **not** enabled at 0.1.0.

**Rationale**: the honest promise is the one the spec makes — same configuration, recorded; same
machine, same result within a stated tolerance. Enabling op determinism buys a stronger claim at a
real cost (it slows training and raises an error for ops that have no deterministic implementation,
which would turn a working model into a refusal), and the claim it buys is still only per-machine.
Principle IV's habit applies to this as much as to a latency figure: state what was measured, not
what sounds better.

**Alternatives considered**: enabling op determinism and advertising bit-identical training
(rejected as above, and recorded as a thing to revisit at the quantize stage, where bit-exactness
becomes meaningful because the quantized flatbuffer *is* comparable byte for byte).

## R10 — The metrics are computed here, not by a dependency

**Decision**: accuracy, macro precision, recall and F1, per-class recall and the confusion matrix,
computed from the confusion matrix in `caravan/metrics/classification.py` with `numpy` only, which
the extra already has through the framework. Every metric is written with the split it was measured
on, the dataset version and the number of samples (FR-007).

**Rationale**: the whole set is a confusion matrix and about thirty lines of arithmetic over it.
Principle XII is explicit that code the project could own in a few hundred readable lines must not
become a dependency, and `scikit-learn` for `f1_score` is the textbook case of that.

**Alternatives considered**: `scikit-learn` (rejected as above); the framework's own metrics
(rejected: Keras metrics are stateful objects tied to training, and macro F1 and the per-class
breakdown would still be computed by hand).

## R11 — Artifact names and formats

**Decision**: the stages write, inside the run directory:

```text
model/built.keras        model/built.json        # shapes, parameter count, per-layer table
model/trained.keras      metrics.json
checkpoints/best.keras   checkpoints/final.keras
training-history.json                            # per-epoch loss and metric values
```

`.keras` is the framework's own archive format. `built.json`, `metrics.json` and
`training-history.json` are written with `sort_keys=True` and a trailing newline, so a diff between
two runs is readable.

**Rationale**: the stage contract of the constitution requires each stage to declare what it reads
and writes, and the next feature (quantize) reads `model/trained.keras` and
`dataset`/`representative_samples` — nothing else. `built.json` exists because FR-003 requires the
shape and parameter count to be *reported*, which means readable by a person and by the next stage,
not only printed.

**Alternatives considered**: the SavedModel directory format (rejected: a directory of protobufs
where a single file does); `.h5` (rejected: legacy, and lossy for some layer configurations);
putting the per-layer table only in the run report (rejected: the report is the record of a run, and
the built model's shape is a property of the artifact).

## R12 — Continuous integration

**Decision**: the test matrix becomes **3.13, 3.14 and 3.15** — 3.13 because the floor now claims
it and Principle XII condition 1 requires the claim to be tested. One new job, `train`, runs on
3.13 only: it installs `.[train]`, runs the training tests, and records the extra's installed size
in the log. The existing `clean-environment` and `install-budget` jobs are untouched, so the default
installation's budget keeps being measured without the framework anywhere near it.

The `train` job may use the uv cache (it measures nothing); `install-budget` still must not.

**Rationale**: a 700 MB download in continuous integration is tolerable once per run on a public
repository's free standard runners; an untested 3.13 claim in the published metadata is not
tolerable at all. The extra's size is *recorded* rather than gated: the constitution's install
budget is about the default installation, and gating a number set by TensorFlow's wheel would be a
gate the project cannot act on.

**Alternatives considered**: skipping 3.13 and trusting it (rejected by the amendment);
gating the extra's install size (rejected as above); running the training tests on every Python
(impossible — the framework installs on 3.13 only).

## R13 — The fixture dataset

**Decision**: `tests/fixtures/datasets/synthetic/` holds `records.csv` and the seeded standard-library
script `make.py` that generated it. A test regenerates it in a temporary directory and asserts the
bytes match, so the committed file provably corresponds to its generator.

Shape: five feature columns and a `label` column; four labels matching the pilot manifest
(`normal`, `dos`, `fuzzy`, `replay`); 20 windows of 64 records per label, plus a deliberate
label-boundary region so that at least one window is discarded (SC-010). That is 5,120-odd records
and roughly 160 KB, under the 200 KB the spec sets.

The acceptance test runs the **pilot manifest** with `dataset.source` pointed at this fixture, as a
separate fixture manifest — the pilot manifest's own source is the author's real dataset path and
stays that way.

**Rationale**: a generator alone would make the test suite depend on generating data every run; a
committed file alone leaves nobody able to say what it is. Both, with an equality test, cost one
test and answer both.

**Alternatives considered**: generating the fixture in a pytest fixture at run time (rejected: the
spec requires a committed fixture, and a generated one cannot be inspected when a test fails);
committing a slice of the real HCRL data (rejected outright — FR-013, and the licence is not the
project's to redistribute).
