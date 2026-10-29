# Phase 0 research: Imagery for the site

Everything below was decided against the clarified spec of 2026-10-27 and measured on 2026-10-28.
Where a figure appears, it was measured here, not carried over from the spec.

## R1 — The site weighs 703 KB, not 880 KB, and the budget must be measured carefully

**Decision**: FR-029's gate measures the **sum of apparent file sizes of the served output,
excluding `.doctrees`**. The ceiling is read as 3,000,000 bytes (decimal), the strict reading.

**Measured**: building `docs/` with the pinned Sphinx 9.2.0 produces 24 HTML pages and 51 served
files. Three ways of measuring the same build disagree badly:

| Method | Figure | Fit for the gate |
|---|---|---|
| `du -sk` on the whole output | 2,044 KB | Wrong — 1,204 KB of it is `.doctrees` build cache that is never served |
| `du -sk` excluding `.doctrees` | 840 KB | Wrong — `du` rounds every file to a 4 KB block, and a site of 51 small files pays ~120 KB of rounding |
| sum of apparent bytes, excluding `.doctrees` | **720,306 B (703.4 KB)** | Correct |

**Rationale**: the gate will be close to binding (R2), so a measurement method that overstates by
17% or by 190% would either fail a site that is fine or pass one that is not. The spec's "about
880 KB" is a rounded, older figure; it is explanatory text, and FR-029's 3 MB ceiling is unaffected.

**Alternatives considered**: `du` was rejected for the block rounding above. Measuring the
repository rather than the build was rejected because the record files and the build output differ,
and FR-029 speaks about the built site.

## R2 — The zoo's byte caps do not protect the site budget; an aggregate cap does

**Decision**: keep the zoo's encoder settings and its per-width caps, and add a **per-record
aggregate cap of 118,000 bytes** across the three derivatives. The site-wide gate of R1 stays the
binding constraint; the aggregate cap exists so a bad image is caught at placement rather than at
the end of the nineteenth.

**Measured**: the zoo's 92 records hold 276 WebP files totalling 9,588 KB — **104 KB per record**
across three widths. Its own caps are `{480: 60_000, 960: 140_000, 1600: 300_000}` bytes, which sum
to 500,000 bytes a record. Nineteen records at that cap would be 9.5 MB: copying the caps alone
would permit a site three times over its ceiling.

The arithmetic that matters:

```text
ceiling                     3,000,000 B
site today                   -720,306 B
credits page (allowance)      -~20,500 B
                            = 2,259,194 B for 19 placed images
                            =   118,905 B per image
zoo's observed rate              106,500 B per image  -> 2,023,500 B
projected total                2,764,300 B (2.64 MB), about 11% margin
```

**Rationale**: the same house style and the same encoder at the same widths already produce 104 KB
an image across 92 samples, so the budget holds with roughly 11% to spare — but not by much, and
not by assumption.

**Refined during implementation (2026-10-28)**: the arithmetic above missed two costs that the
first real build revealed. Publishing each record's `image.yaml` beside its derivatives adds about
1.7 KB an image (~32 KB over nineteen), and the credits page plus the footer link on 22 pages costs
about 5 KB before any image exists and grows ~400 bytes a record. The projection becomes roughly
2,788,000 bytes, about **93% of the ceiling — a 7% margin, not 11%**. The gate measured 725,361
bytes with no image placed and 740,358 with one synthetic image in. The aggregate cap of 118,000 B is the per-image share of the ceiling, so an
image that passes it cannot be the reason the site fails.

**Alternatives considered**: dropping the 1600 px width for non-hero subjects would free ~50 KB an
image and end the tightness, but the owner chose the zoo's three widths explicitly. AVIF would
compress better than WebP but is a second encoder and a second format to serve. Both stay on the
shelf as the named remedies if the first real derivatives come in heavier than the zoo's — which is
a measurement to take early, not a risk to carry silently to the end.

**Not measured, and why**: a lower bound from Caravan's existing flat SVG art was attempted and
abandoned — rasterising SVG needs a cairo library this machine does not have. It would have been
weaker evidence anyway: the zoo's 92 images are the same screenprint style, the same models and the
same encoder, which is as close to a direct measurement as is available before the first round runs.

## R3 — The AI-provenance marker needs Pillow and nothing else

**Decision**: write the IPTC marker exactly as the zoo does, through Pillow's WebP encoder.

The marker is the literal
`http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia`, carried in an XMP packet
with two fields — `Iptc4xmpExt:DigitalSourceType` holding that URI, and `xmp:CreatorTool` naming
the series and the model — and passed straight to the encoder as `save(..., "WEBP", quality=q,
method=6, xmp=packet)`.

**Rationale**: this is the standard IPTC code for media produced by a generative model, so the
disclosure of FR-032 travels inside the file when it leaves the page. It costs no dependency beyond
Pillow, which `sheet.py` already declares.

**Alternatives considered**: C2PA signing is the richer standard but needs a signing identity and a
toolchain, which FR-011's "no account, no token, no credential" rules out. Writing EXIF instead was
rejected because WebP's EXIF support is weaker and the IPTC code is defined for XMP.

## R4 — Two thirds of the zoo's record is triage scaffolding and must not come along

**Decision**: port the record shape, minus every field that exists only to feed a check this
feature does not port (FR-007's second sentence).

Kept: `id`, `series`, `theme`, `subject`, `generation` (the whole recipe), `licence`, `placements`,
`scene`, `alt`, `focal_point`, `aspect`, `source`, `derivatives`.

Dropped, with the reason: `checks.faces`, `checks.text`, `checks.style`, `checks.duplicate` and
`faces_below_threshold` (automatic triage, not ported); `measures.phash` and every `accent_*` and
`other_share` measure (feed the style and near-duplicate checks); `round` and the empty-`placements`
pool convention (the pool overview, not ported); `theme` as a closed enum of the zoo's ten themes
(feeds the zoo's coverage check — Caravan keeps `theme` as a free string).

`licence` keeps the zoo's constant `CC0-1.0`, which is what the clarification chose independently,
and `alt` keeps the schema's requirement that it end in `(AI-generated image)`, which is FR-028.

**Rationale**: a threshold whose check is absent is dead configuration that later reads as a
promise. FR-007 says so directly.

## R5 — The credits page is written by the placement command, not by the site build

**Decision**: `place.py` writes `docs/credits.md` from the records and commits it like any other
page; Sphinx renders it with no knowledge of this feature.

**Rationale**: FR-010 forbids the site build invoking any of this, and the zoo's own approach —
rendering `credits.html.j2` inside its build from a live record scan — would break that. Writing the
page at placement time keeps the build ignorant, costs the CI job nothing, and still cannot drift,
because the page is rewritten from the records on every placement.

Per entry the page carries what the zoo's carries: the image, the scene as its heading, a
disclosure sentence naming the model, its licence, the hardware class and the date, then the model
card link, where the image is used, and the CC0-1.0 deed.

**Alternatives considered**: a Sphinx extension generating the page at build time was rejected by
FR-010. A hand-written page was rejected because nineteen entries copied by hand is exactly the
drift FR-033 exists to prevent.

## R6 — One footer link in the theme layout, not a per-page condition

**Decision**: add the credits link to the single footer in `docs/_themes/caravan/layout.html`, with
link text containing "AI-generated", so it appears on all 24 pages.

**Rationale**: FR-034 requires the link on every page that shows a generated image. The zoo gates
its link on a per-page `has_images` flag computed in its own build; Sphinx would need a build hook
to know the same thing, which FR-010 forbids. Putting the link on every page is a superset of what
FR-034 asks, needs no build logic, and gives the footer one shape instead of two. The theme already
writes the footer once, so this is a one-line change.

## R7 — Where the records live, and how Sphinx serves them

**Decision**: `docs/_static/images/<id>/`, with `html_static_path = ["_static"]` added to
`docs/conf.py`. Sphinx copies the tree verbatim to `_build/html/_static/images/`.

**Rationale**: `conf.py` currently sets only `html_theme_path`, so the theme's own static directory
is the only one copied — and the theme is the design system, not a place for content. A sibling
`_static` keeps the derivatives and the record together, publishes the record alongside the image
(so FR-020's traceability is a fact a reader can check, not a repository convention), and needs no
build step of ours. The 19 `image.yaml` files add about 50 KB, which R2's arithmetic already carries.

**Alternatives considered**: putting the images in the theme's `static/img/` was rejected for mixing
content into the design system. Keeping records outside `docs/` and copying only derivatives in was
rejected because it needs a copy step, and a copy step in the build is FR-010 again.

## R8 — The draft model cannot take the negative prompt

**Decision**: accept it, and say so in the series file and the README.

The draft model is FLUX.2-klein-4B, which takes no negative prompt; the generator only passes one
when the model declares `true_cfg_scale`, which the final model (Qwen-Image-2512) does. So a draft
pass answers "does the model understand this subject at all" without the negative list, and the
clichés FR-005 names are only excluded on the final pass.

**Rationale**: the draft exists to test comprehension at a few seconds an image, not to produce
candidates. Rejecting a draft for lettering the negative prompt would have suppressed would be
reading the wrong signal from it.

## R9 — FR-009 and the generator's dependencies

**Decision**: `sheet.py` and `place.py` carry PEP 723 inline dependencies; `gen.py`'s dependencies
are declared by the `Dockerfile` beside it.

**Rationale**: FR-009 asks that the scripts declare their own dependencies so they run without
installing anything into the project, and nothing is installed into the project either way —
`pyproject.toml` is untouched. `gen.py` needs torch and diffusers on a CUDA machine; a PEP 723
header promising `uv run --script` would work is a promise it cannot keep, since the container is
what makes those imports possible. The declaration is honest where it is.

## R10 — Twenty subjects, nineteen placements

**Decision**: the series carries twenty subjects, of which nineteen name a place on the site and one
(`gate/cleared`) is held in reserve. FR-004's twenty is satisfied; SC-003's "fifteen of the twenty"
counts all twenty, reserve included.

**Measured**: the series file has 20 subject entries and 20 `placement:` lines, one reading
"reserve — a passing verdict". The nineteen placed ones cover every page FR-004 names: the first
screen, the four legs, the route index, the four concept pages, the four reference pages, the
budgets page, what is verified today, the roadmap, the board runs, and the data wherever it is
explained.

**Rationale**: this was the one item left Outstanding after clarification. It needed counting, not
deciding.

## R11 — What a naive copy would drag in

Recorded because the cost of this feature depends on it. The zoo's placement command has no
standalone record builder: it routes through `images_triage` for building and writing a record, and
its record loader reaches into the zoo's model and topic registry. `images_process` imports opencv,
numpy, rapidocr and a network-fetched face model.

Only five functions are wanted — the focal crop, the XMP packet, the encode, the derivative set and
the marker read — and those need Pillow alone. `place.py` therefore writes its own record builder
rather than porting the zoo's, which is also what keeps FR-008 and Principle XII true.
