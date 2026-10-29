# Phase 1 data model: Imagery for the site

Six entities, three files. Nothing here is a database and nothing is part of the distribution: the
series is hand-written, the manifest and the picks are produced by a round, and the record is what
gets committed.

## Series — `scripts/imagery/series/siebdruck.yaml`

The art direction, and the only file a reviewer needs to read to know what the pictures will be.

| Field | Type | Rules |
|---|---|---|
| `name` | string | The series name, recorded in every manifest entry and record (FR-018). |
| `style` | string | One sentence appended to every subject's prompt. Whitespace is collapsed on load. Reserves the warm accent for the one object the picture is about (FR-003). |
| `negative` | string | The negative prompt. Names this subject matter's clichés — glowing brains, circuit traces, server racks, floating interface elements — as well as the generic ones (FR-005). Applied only by a model that takes one (R8). |
| `models.draft` / `models.final` | object | `id`, `pipeline`, `steps`, `licence`, `card`, and `guidance` or `true_cfg_scale`. Both Apache-2.0 and ungated (FR-001). |
| `themes` | map of theme id → list of Subject | Grouping; the theme id is a free string, not the zoo's closed enum (R4). |

## Subject — an entry under `themes.<theme>`

One picture to be made.

| Field | Type | Rules |
|---|---|---|
| `id` | string | Unique within its theme (FR-002). With the theme it forms the key `theme/id`, which the seed is derived from. |
| `prompt` | string | What is sent to the model, before `style` is appended. |
| `aspect` | `16:9` \| `3:2` | Chooses the render size: 1344×768 or 1200×800. |
| `scene` | string | One line for the credits page. |
| `alt` | string | The text alternative. Written to be read aloud, and must end in `(AI-generated image)` once placed (FR-028). |
| `placement` | string | The place on the site this is intended for (FR-002). |
| `reserve` | bool, default false | Held back from a normal run; 1 of the 20 subjects (R10). |

**Invariants**: 20 subjects, 19 of them placed (FR-004, R10); no subject is a repeat of another;
every subject has a prompt, a placement and an alt text (story 1's independent test).

## Round — a directory of images plus `manifest.json`

One rendering of a series, on the owner's machine. **Never committed**: ~80 PNGs at full size are
not repository material, and only the picked ones become records.

| Field | Type | Rules |
|---|---|---|
| `series`, `model` | string | The series name and the model id of the run. |
| `images[]` | array | One entry per rendered file. |

Each `images[]` entry is the only provenance a placed image will ever have, and carries every field
FR-018 names: `file`, `theme`, `subject`, `aspect`, `prompt` and `negative_prompt` as sent, `seed`,
`seed_base`, `steps`, `guidance`, `width`, `height`, `model`, `revision` (the revision actually
loaded), `model_licence`, `model_card`, `pipeline`, `series`, `generated`, `hardware`, `seconds`,
and `generator` = `{commit, image_digest, script_sha256}`.

**Seed rule** (FR-013): `seed = seed_base + (97 * crc32("theme/subject")) % 1_000_000 + i`. A
subject keeps its seeds across runs, no two subjects share one, and a later round offsets every
seed with `--seed-base`.

**File name**: `<theme>--<subject>--<seed>.png`, which is what makes an existing file skippable and
an interrupted run resumable (FR-014).

## Candidate — one image in a round

One subject at one seed. Not a stored entity: it is a file in the round plus its manifest entry. The
contact sheet numbers candidates **within their subject**, starting at 1, in seed order; that number
is what a pick names, and it is meaningful only against the round that produced it.

## Picks — `picks.yaml`, downloaded from the contact sheet

The owner's decision, and the only thing that crosses from the sheet back to the repository.

```yaml
picks:
  route/road-to-the-board: 2      # the candidate number within that subject
  gate/the-barrier: none          # needs another round
```

**Rules**: exactly one entry per subject the sheet showed; the value is a positive integer or
`none` (FR-023). A subject with no candidate at all is shown as such and recorded as `none`
(FR-024).

## Placement record — `docs/_static/images/<id>/image.yaml`

A picked image brought into the repository. One directory per image, holding three derivatives and
this record. Committed; this is the feature's only lasting artifact.

| Field | Type | Rules |
|---|---|---|
| `id` | slug | `^[a-z0-9]+(-[a-z0-9]+)*$`, unique across the site. Names the directory and the derivative files. |
| `series`, `theme`, `subject` | string | Where it came from in the art direction. |
| `generation` | object | The recipe, copied verbatim from the manifest entry: `model`, `revision`, `model_licence`, `model_card`, `pipeline`, `prompt`, `negative_prompt`, `seed`, `steps`, `guidance`, `width`, `height`, `generated`, `hardware`, `generator.{commit,image_digest,script_sha256}`. This is FR-018 surviving placement (FR-020). |
| `licence` | const `CC0-1.0` | The image's own licence (FR-030). |
| `placements[]` | array of string, non-empty | The pages this image appears on. Never empty — Caravan has no pool (R4). |
| `scene` | string | One line, for the credits page. |
| `alt` | string | Must end `(AI-generated image)` (FR-028). |
| `focal_point` | [x, y] | Fractions in 0–1; the centre of the crop. |
| `aspect` | `16:9` \| `3:2` | The crop taken from the render. |
| `source` | object | `width`, `height`, `sha256` of the render. The PNG itself is **not** copied in. |
| `derivatives` | map 480\|960\|1600 → object | `file` (`*.webp`), `bytes`, `sha256`. |

**Invariants**:
- No record without a manifest entry for the file it came from (FR-019) — the refusal is the
  placement command's, and it is non-zero exit, nothing written.
- Every derivative carries the IPTC `trainedAlgorithmicMedia` marker (FR-032, R3).
- `sum(derivatives[*].bytes) <= 118_000` (R2), and no derivative above the zoo's per-width cap.
- No zoo-era triage field is present (FR-007, R4).

## Credits entry — derived, not stored

One per record, in `id` order, written into `docs/credits.md` by the placement command (R5). Carries
the image, the scene as heading, a disclosure sentence naming the model, its licence, the hardware
class and the date, then the model card link, the pages it is used on, and the CC0-1.0 deed. Derived
on every placement, so it cannot drift from the records (FR-033).

## Lifecycle

```text
Series ──render──> Round (manifest.json + ~80 PNGs, on the owner's machine)
                     │
                     └──contact sheet──> Picks (picks.yaml)
                                           │
Round + Picks ──place.py──> Placement records ──> docs/credits.md + the pages
                               │
                               └── refused if the file has no manifest entry (FR-019)
```

A subject whose pick is `none` goes back to a second round with `--seed-base` offset, and its SVG —
where it had one — stays until a replacement is actually placed (FR-031).
