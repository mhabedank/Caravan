# Contract: the three commands

None of these is part of the distribution, none appears in Caravan's CLI, and none is invoked by the
site build (FR-008, FR-010). They are standalone scripts under `scripts/imagery/`.

## 1. `gen.py` — render a round *(exists)*

Runs inside the `caravan-flux` container on a CUDA machine. Dependencies come from the `Dockerfile`
(R9).

| Option | Default | Meaning |
|---|---|---|
| `--series PATH` | required | The series file. |
| `--model draft\|final` | `final` | The draft model answers "does it understand the subject at all" at a few seconds an image (FR-016). |
| `--seeds N` | 1 | Seeds per subject. A full round uses 4. |
| `--seed-base N` | 0 | Added to every seed, so a second round cannot repeat the first's (FR-013). |
| `--steps N` | 0 → the model's own | Step count override. |
| `--only LIST` | "" | Comma-separated themes or `theme/subject` keys (FR-015). |
| `--reserve` | off | Include subjects marked reserve. |
| `--out DIR` | required | The round directory. |
| `--plan` | off | Print the files a run would write and touch no GPU (FR-017). |

**Behaviour**: writes `<out>/<theme>--<subject>--<seed>.png` and one `manifest.json` entry per
image. An existing file is skipped, so an interrupted run resumes (FR-014). With no `--only`, a
`next.txt` in the output directory supplies the subjects of a follow-up round (FR-015).

**Exit**: 0 on success. Non-zero on an unreadable series file or an unknown model key.

## 2. `sheet.py` — the two pages *(exists)*

A PEP 723 script: `uv run --script` fetches `pyyaml` and `pillow` into a throwaway environment.
Both pages are local files that open without a server and send nothing anywhere (FR-025).

```text
sheet.py subjects <series.yaml> [--out PATH]    # before the GPU runs
sheet.py round <round-dir>                      # after it
```

`subjects` builds from the series file alone, with no rendered image, and states the style and
negative sentences in full (FR-021). `round` groups candidates under their subject, numbers them
within the subject, shows each subject's prompt, links each candidate to its full-size file
(FR-022), keeps picks across a reload in browser storage, writes them out as `picks.yaml` (FR-023),
and shows a subject with no candidate as a subject with no candidate (FR-024). Both use the site's
four inks and work in the light and the dark scheme (FR-026).

## 3. `place.py` — bring a picked image in *(new)*

A PEP 723 script declaring `pyyaml>=6` and `pillow>=11`. Pillow does the crop, the encode and the
XMP marker; nothing else is needed (R3, R11).

```text
place.py <round-dir> --picks picks.yaml [--only theme/subject] [--dry-run]
```

| Option | Default | Meaning |
|---|---|---|
| `<round-dir>` | required | The round holding the images and `manifest.json`. |
| `--picks PATH` | required | The `picks.yaml` downloaded from the contact sheet. |
| `--only KEY` | all | Place one subject rather than every picked one. |
| `--focal "x,y"` | `0.5,0.5` | The centre of the crop, as fractions. |
| `--id SLUG` | derived | Override the record id, otherwise derived from the subject. |
| `--dry-run` | off | Report what would be written, write nothing. |

**Order of operations**, per picked subject:

1. Resolve the candidate number to a file in the round; `none` is skipped.
2. **Find the file's entry in `manifest.json`. If there is none, refuse** (FR-019).
3. Crop to the subject's aspect around the focal point; encode 480, 960 and 1600 px WebP at
   descending quality until each is inside its per-width cap, with the IPTC
   `trainedAlgorithmicMedia` XMP packet written into every one (FR-027, FR-032).
4. Check the three derivatives together against the aggregate cap of 118,000 bytes (R2).
5. Write `docs/_static/images/<id>/` — three `.webp` files and `image.yaml`.
6. Rewrite `docs/credits.md` from every record on disk (FR-033, R5).

**Refusals**, each non-zero exit with nothing written:

| Condition | Message |
|---|---|
| The file has no `manifest.json` entry | `<file> is not in <manifest>` — no provenance, no placement (FR-019) |
| The target directory already exists | `<dir> exists; remove it first` |
| The three derivatives exceed 118,000 bytes | names the figure and the per-image share of the site budget (R2) |
| A derivative stays above its per-width cap at the lowest quality | names the width and the cap |
| The subject has no `alt` or no `scene` in the series | names the subject and what is missing |

**Idempotence**: placing the same pick twice is refused by the existing-directory rule, not silently
overwritten. Re-placing means removing the record directory first, which is deliberate: a record is
provenance, and provenance is not quietly replaced.

## 4. The weight gate

See [weight-gate.md](./weight-gate.md).
