# Website imagery: rendering on the DGX Spark

The images of the Caravan site are **generated, never fetched**. This directory holds the art
direction, the generator and its container. Nothing here is part of the distribution: `caravan-ml`
does not depend on it, the site build never calls it, and the two scripts carry their own
dependencies inline (PEP 723) so they add nothing to `pyproject.toml`.

**Copied, not shared.** The method comes from the Mobility Model Zoo's features 016 and 019
(`scripts/imagery/`, `zoo/site/images/series/siebdruck.yaml`), copied on 2026-10-27. The
constitution forbids depending on the zoo, so this is a copy for the same reason the design tokens
are: no package, no submodule, nothing fetched at build time. The two may drift and nothing keeps
them in step.

**What is not copied:** the zoo's feature 019 — image records, automatic triage (faces, text,
palette, near-duplicates), derivative generation, a credits page and a coverage check. That is
about 1,600 lines of Python and several dependencies, for a library of a hundred-odd images across
many themes. Caravan is asking for twenty. The contact sheet here shows every candidate and the
owner looks at all of them, which is what the zoo's automatic rejection exists to avoid at its
scale and does not need to be at this one. If the library grows, port it then.

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
the model understand the subject at all? Where it does not, rewrite that subject's prompt and
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

## 7. What a picked image still needs

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
