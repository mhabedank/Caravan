# Website imagery: rendering on the DGX Spark

The images of the Caravan site are **generated, never fetched**. This directory holds the art
direction, the generator and its container. Nothing here is part of the distribution: `caravan-ml`
does not depend on it, the site build never calls it, and the two scripts carry their own
dependencies inline (PEP 723) so they add nothing to `pyproject.toml`.

**Copied, not shared.** The method comes from the Mobility Model Zoo's features 016 and 019
(`scripts/imagery/`, `zoo/site/images/series/siebdruck.yaml`, `src/mobility_model_zoo/site/`),
copied on 2026-10-27 and extended on 2026-10-28 with the placement half: the record directory, the
three WebP derivatives, the IPTC marker and the credits page. The constitution forbids depending on
the zoo, so this is a copy for the same reason the design tokens are: no package, no submodule,
nothing fetched at build time. The two may drift and nothing keeps them in step.

**What is not copied:** the triage half of the zoo's feature 019 — automatic rejection by face,
text, palette and near-duplicate checks, the coverage check and the pool overview. That is about 520
of its 1,600 lines and it carries opencv, onnxruntime, rapidocr and a fetched face model, for a
library of a hundred-odd images across many themes. Caravan is asking for twenty. The contact sheet
here shows every candidate and the owner looks at all of them, which is what the zoo's automatic
rejection exists to avoid at its scale and does not need to be at this one. If the library grows,
port it then.

What **is** copied, because the images on a public page need it: the record directory with its three
derivatives, the IPTC `trainedAlgorithmicMedia` marker inside every WebP, and the credits page. Those
need Pillow and nothing else. `place.py` writes its own record builder rather than porting the zoo's,
which routes through the triage module this repository does not have.

Hardware: a machine with a CUDA GPU. The DGX Spark over the VPN is the one this was written for;
anything with enough VRAM works.

## 1. Build the container (once)

```bash
docker build -t caravan-flux scripts/imagery
```

## 2. Cache the models (once)

Both models are Apache-2.0 and not gated. No Hugging Face token is needed.

```bash
docker run --rm -e HF_HUB_DISABLE_XET=1 -v ~/.cache/huggingface:/root/.cache/huggingface caravan-flux \
  python -c "from huggingface_hub import snapshot_download as d; d('black-forest-labs/FLUX.2-klein-4B'); d('Qwen/Qwen-Image-2512')"
```

## 3. Decide the subjects before spending the GPU

```bash
uv run --script scripts/imagery/sheet.py subjects scripts/imagery/series/siebdruck.yaml \
  --out ~/caravan-imagery/subjects.html
```

One page listing all twenty subjects, their prompts and where each is meant to go. Reading it
costs a minute; a full round costs hours. Change the prompts in the series file, not afterwards.

## 4. Draft pass

```bash
cp -r scripts/imagery ~/caravan-imagery/
docker run --rm --gpus all --ipc=host \
  -e CARAVAN_GEN_COMMIT=$(git rev-parse --short HEAD) \
  -e CARAVAN_GEN_IMAGE=$(docker inspect --format '{{index .RepoDigests 0}}' caravan-flux 2>/dev/null || docker images --no-trunc -q caravan-flux) \
  -v ~/.cache/huggingface:/root/.cache/huggingface -v ~/caravan-imagery:/work caravan-flux \
  python /work/imagery/gen.py --series /work/imagery/series/siebdruck.yaml \
    --model draft --seeds 2 --out /work/rounds/draft
```

About four seconds an image, so forty images in three minutes. The draft is for one question: does
the model understand the subject at all? Note that the draft model takes **no negative prompt** —
`gen.py` only sends one to a model declaring `true_cfg_scale`, which is the final model — so the
clichés in the series' `negative` are excluded on the final pass only. Do not reject a draft for
stray lettering; that is not what a draft can tell you. Where it does not, rewrite that subject's prompt and
re-draft only it with `--only workshop/the-callipers`.

## 5. Final pass

```bash
docker run --rm --gpus all --ipc=host \
  -e CARAVAN_GEN_COMMIT=$(git rev-parse --short HEAD) \
  -e CARAVAN_GEN_IMAGE=$(docker images --no-trunc -q caravan-flux) \
  -v ~/.cache/huggingface:/root/.cache/huggingface -v ~/caravan-imagery:/work caravan-flux \
  python /work/imagery/gen.py --series /work/imagery/series/siebdruck.yaml \
    --model final --seeds 4 --out /work/rounds/1
```

Twenty subjects × four seeds = eighty images at about three minutes each on a GB10: **roughly four
hours**. Run it detached with a log — `nohup … > rounds/1/render.log &` — and note that existing
files are skipped, so an interrupted run resumes where it stopped.

`--plan` prints the file names a run would write and touches no GPU. Use it to check the count
before starting.

## 6. The contact sheet, and picking

```bash
uv run --script scripts/imagery/sheet.py round ~/caravan-imagery/rounds/1
open ~/caravan-imagery/rounds/1/sheet.html
```

The sheet groups every candidate under its subject and numbers it. Click a picture to pick it for
that subject, or "none of these" when the subject needs another round. Picks are kept in the
browser; "Download picks.yaml" writes them out.

A second round renders only what is still open, with new seeds:

```bash
# put the `none` subjects in next.txt, one `theme/subject` per line
python /work/imagery/gen.py --series /work/imagery/series/siebdruck.yaml \
  --model final --seeds 4 --seed-base 1000 --out /work/rounds/2
```

## 7. Placement

```bash
uv run --script scripts/imagery/place.py ~/caravan-imagery/rounds/1 \
  --picks ~/Downloads/picks.yaml --dry-run      # see it first
uv run --script scripts/imagery/place.py ~/caravan-imagery/rounds/1 \
  --picks ~/Downloads/picks.yaml
```

Each picked image becomes one directory under `docs/_static/images/<theme>-<subject>/`: three WebP
derivatives at 480, 960 and 1600 px, every one carrying the IPTC `trainedAlgorithmicMedia` marker,
and an `image.yaml` holding the recipe copied from the round's manifest. `docs/credits.md` is then
rewritten from every record on disk, so it cannot drift from them. Sphinx copies the tree verbatim;
the site build runs none of this.

A subject's crop centre comes from an optional `focal: [x, y]` in the series file, falling back to
`--focal` and then to the middle. One focal point for nineteen pictures would be wrong, which is
why the series can carry its own.

**What it refuses**, each with a non-zero exit and nothing written:

| Refusal | Why |
|---|---|
| the manifest entry does not carry the whole recipe | No provenance, no placement. An image traceable to half a recipe is not traceable. Placement is driven by the manifest, so a file the manifest does not know about is never a candidate — that case cannot arise. |
| the record directory already exists | A record is provenance, and provenance is not quietly overwritten. Remove it first, deliberately. |
| the three derivatives exceed 118,000 bytes | That is one image's share of the site's 3,000,000 byte ceiling. The remedy is fewer widths or another format, not a larger number. |
| a derivative stays above its per-width cap at quality 60 | The image is too busy for the budget at that width. |
| the subject has no `alt` or no `scene` | A picture on a public page without a text alternative is not placed. |

The weight gate in `.github/workflows/docs-checks.yml` is what actually holds the budget: it sums
the bytes the built site serves and fails above 3,000,000. The per-image cap only catches a bad
image early.

## 8. What a picked image still needs

Nothing here imports an image into the site. That is a separate decision, and it carries
obligations the generator cannot discharge:

- **Provenance.** `manifest.json` records, per image, the exact recipe: model id and revision, its
  licence and model card, the full prompt and negative prompt, the seed, the step count, the
  guidance, the container digest and this script's SHA-256. An imported image keeps that record;
  an image without one does not go on the site.
- **Weight.** The site is currently 880 KB in total. Eighty PNGs are not, and even twenty placed
  images need derivatives at the widths the pages actually use, not the 1344 px render.
- **A text alternative.** Every subject in the series file carries `alt` and `scene` already; they
  are written to be read aloud, not to describe pixels.
