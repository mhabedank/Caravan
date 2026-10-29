# Quickstart: validating the imagery feature

How to prove each story works. Stories 1, 3 and 4 run on an ordinary machine; story 2 needs the
CUDA machine, which is why it is written to be run by the owner rather than by a session
(Assumptions).

## Prerequisites

- `uv` on the path. Nothing is installed into the project: the scripts are PEP 723 and
  `pyproject.toml` stays byte-identical (FR-008).
- For story 2 only: a CUDA machine with Docker and enough VRAM, and the two models cached. No
  account and no token — both models are Apache-2.0 and ungated (FR-011).

## Story 1 — the subjects, before any GPU time

```bash
uv run --script scripts/imagery/sheet.py subjects \
  scripts/imagery/series/siebdruck.yaml --out /tmp/subjects.html
open /tmp/subjects.html
```

**Expect**: 20 subjects grouped by theme, each with its prompt, aspect, intended placement and alt
text; the style and negative sentences stated once in full; 19 subjects naming a page and one marked
reserve (R10). Reading it should take minutes, not half an hour (SC-001).

**Also check**: edit one prompt in the series file, rebuild, and confirm the page shows that change
and nothing else moved.

## Story 2 — a round *(on the CUDA machine)*

Check the plan before spending anything — this touches no GPU (FR-017):

```bash
python /work/imagery/gen.py --series /work/imagery/series/siebdruck.yaml \
  --model final --seeds 4 --out /work/rounds/1 --plan | wc -l     # expect 76
```

Nineteen placed subjects at four seeds is 76 files; adding `--reserve` makes it 80.

A draft pass first, at a few seconds an image, to find the subjects the model does not understand:

```bash
docker run --rm --gpus all --ipc=host \
  -e CARAVAN_GEN_COMMIT=$(git rev-parse --short HEAD) \
  -e CARAVAN_GEN_IMAGE=$(docker images --no-trunc -q caravan-flux) \
  -v ~/.cache/huggingface:/root/.cache/huggingface -v ~/caravan-imagery:/work caravan-flux \
  python /work/imagery/gen.py --series /work/imagery/series/siebdruck.yaml \
    --model draft --seeds 2 --out /work/rounds/draft
```

Then the final pass with `--model final --seeds 4 --out /work/rounds/1`, about four hours unattended.

**Expect**: one file per subject per seed, named `<theme>--<subject>--<seed>.png`, and one
`manifest.json` entry per file carrying every field of FR-018.

**Resume check (FR-014)**: interrupt the run, start the same command again, and confirm it renders
only what is missing and leaves existing entries untouched.

**Reproducibility check (SC-005)**: re-render one subject at the same seed on the same machine and
confirm the image is identical. On different hardware it will not be, which is why the manifest
records the hardware class.

## Story 3 — picking

```bash
uv run --script scripts/imagery/sheet.py round ~/caravan-imagery/rounds/1
open ~/caravan-imagery/rounds/1/sheet.html
```

**Expect**: every candidate under its subject, numbered within the subject, each linking its
full-size file, with the subject's prompt shown. Candidates large enough to see stray lettering in —
that is the most common reason to reject one.

**Check**: pick some, mark one subject "none of these", reload the page, and confirm the picks
survived. Then download `picks.yaml` and confirm it names one number or `none` for every subject
(FR-023). A subject with no candidate must appear as such, not be omitted (FR-024).

Deciding a whole round should take under half an hour (SC-004), and at least 15 of the 20 subjects
should have something worth placing (SC-003).

## Story 4 — placement

```bash
uv run --script scripts/imagery/place.py ~/caravan-imagery/rounds/1 \
  --picks ~/Downloads/picks.yaml --dry-run      # see it first
uv run --script scripts/imagery/place.py ~/caravan-imagery/rounds/1 \
  --picks ~/Downloads/picks.yaml
```

**Expect**: one `docs/_static/images/<id>/` per picked subject, each holding three WebP derivatives
and an `image.yaml` validating against
[contracts/image-record.schema.json](./contracts/image-record.schema.json); plus a rewritten
`docs/credits.md`.

**The refusal that matters (FR-019)** — the whole point of the provenance rule:

Placement is driven by the manifest, so a file the manifest does not know about is never a
candidate and cannot be picked — that much is structural. What has to be checked is the case that
*can* happen: an entry that exists but does not carry the whole recipe.

```bash
# take a copy of the round, then strip one provenance field from one entry
python3 - <<'EOF'
import json; p = "/tmp/round-probe/manifest.json"; d = json.load(open(p))
del d["images"][0]["revision"]; json.dump(d, open(p, "w"))
EOF
uv run --script scripts/imagery/place.py /tmp/round-probe --picks picks.yaml
# expect: exit 1, "...carries no revision - that is not provenance", nothing written
```

Verified on 2026-10-28: exit 1 on an incomplete entry, exit 1 on an existing record directory,
exit 1 on a candidate number that was never rendered, and in every case nothing written.

**Disclosure (FR-028, FR-032–034)**:

```bash
grep -c "(AI-generated image)" docs/_static/images/*/image.yaml      # one per record
# NOT plain grep for the marker: these are binary files and grep's binary handling will tell you
# the marker is absent when it is present.
python3 -c "
from pathlib import Path
for f in sorted(Path('docs/_static/images').rglob('*.webp')):
    assert b'trainedAlgorithmicMedia' in f.read_bytes(), f
print('every derivative carries the marker')"
```

Then build the site and confirm the credits page names every placed image with its model, licence,
date and hardware class, and that the footer of every page links it with the words "AI-generated".

## The weight gate (FR-029, SC-009)

```bash
uv run --no-project --with sphinx==9.2.0 --with myst-parser==5.1.0 \
  sphinx-build -q -b html docs /tmp/site
find /tmp/site -path /tmp/site/.doctrees -prune -o -type f -print0 \
  | xargs -0 stat -f "%z" | awk '{s+=$1} END {printf "%d B (%.0f%% of 3000000)\n", s, s*100/3000000}'
```

**Expect before any image is placed**: 725,361 B — 24% of the ceiling. (The feature's fixed cost
over the 720,306 B the site served before it is about 5 KB: the credits page and the footer link on
22 pages.) **Expect with all 19 images placed**: about
2,764,300 B, roughly 92%. Over 3,000,000 the gate fails with a non-zero exit and nothing raises it
(see [contracts/weight-gate.md](./contracts/weight-gate.md)).

If the first real derivatives come in heavier than the zoo's 104 KB an image, the margin is gone and
the remedies are named in research R2 — drop the 1600 px width off the non-hero subjects, or move to
AVIF. Both reopen a decision the owner already made, so they are a conversation, not a silent fix.

## Retiring the SVGs (FR-031)

Only after a replacement is actually placed: `hero.svg` and `leg-1.svg` … `leg-4.svg` go;
`favicon.svg` and `mark.svg` are brand marks and stay. A subject that never produced a usable
candidate keeps the SVG it has today — the page must never end up worse than it is now.

## What "done" looks like

- `pyproject.toml` unchanged, no new extra, no new dependency group (FR-008, SC-006).
- The `docs-checks` job still inside ten minutes (SC-007).
- Every placed image traceable to the run that made it, and re-renderable from its record on the
  same hardware (SC-005).
- The built site under 3,000,000 bytes with every placed image in it (SC-009).
