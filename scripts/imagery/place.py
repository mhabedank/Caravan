# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml>=6", "pillow>=11"]
# ///
"""Bring a picked image into the repository as a record.

COPIED IN SHAPE from the Mobility Model Zoo's feature 019 (`src/mobility_model_zoo/site/images.py`,
`images_process.py`, `images_cli.py`), on 2026-10-28: the record directory, the three WebP
derivatives, the IPTC marker and the credits page. The zoo's triage half — faces, text, palette and
near-duplicate rejection, the coverage check, the pool — is NOT copied, and the record builder here
is written fresh rather than ported, because the zoo's routes through that triage module. The
constitution forbids depending on the zoo; see README.md. The two may drift.

Reads a round (its images and `manifest.json`) and the `picks.yaml` downloaded from the contact
sheet, and writes one directory per picked image under `docs/_static/images/<id>/`: three WebP
derivatives at 480, 960 and 1600 px and an `image.yaml` holding the recipe that made the image.
Then it rewrites `docs/credits.md` from every record on disk.

**No provenance, no placement.** An image whose file has no entry in the round's manifest is
refused, and nothing is written. The manifest is the only provenance a placed image will ever have.

Nothing here is part of the distribution. It is a PEP 723 script: `uv run --script` fetches its two
dependencies into a throwaway environment, and `pyproject.toml` is untouched.

    uv run --script scripts/imagery/place.py ~/caravan-imagery/rounds/1 \
        --picks ~/Downloads/picks.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

WIDTHS = (480, 960, 1600)
# The zoo's per-derivative caps. They bound one file; they do not bound the site (research R2).
BYTE_CAPS = {480: 60_000, 960: 140_000, 1600: 300_000}
# One image's share of the 3,000,000 byte site ceiling (FR-029). This is the cap that protects it.
AGGREGATE_CAP = 118_000
QUALITIES = (72, 68, 64, 60)
IPTC_MARKER = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
LICENCE = "CC0-1.0"
LICENCE_DEED = "https://creativecommons.org/publicdomain/zero/1.0/"
ALT_SUFFIX = "(AI-generated image)"
DISCLOSURE = "AI-generated"
ASPECTS = {"16:9": 16 / 9, "3:2": 3 / 2}

# Every field FR-018 requires a manifest entry to carry. Placement is driven by the manifest, so an
# unknown file is never a candidate in the first place; what FR-019 has to catch is an entry that
# exists but does not carry the recipe. A record built from half a recipe is not traceable, which
# is the whole point of refusing.
REQUIRED_PROVENANCE = (
    "model", "revision", "model_licence", "model_card", "pipeline", "prompt", "seed", "steps",
    "guidance", "width", "height", "series", "generated", "hardware", "generator",
)
REQUIRED_GENERATOR = ("commit", "image_digest", "script_sha256")

REPO = Path(__file__).resolve().parents[2]
IMAGES = REPO / "docs" / "_static" / "images"
CREDITS = REPO / "docs" / "credits.md"


def refuse(message: str) -> None:
    """Every refusal leaves the repository exactly as it was: a half-record is worse than none."""
    sys.exit(f"refused: {message}")


def load_series(path: Path) -> dict:
    import yaml

    series = yaml.safe_load(path.read_text(encoding="utf-8"))
    series["style"] = " ".join(series["style"].split())
    series["negative"] = " ".join(series.get("negative", "").split())
    return series


def subject_map(series: dict) -> dict[str, dict]:
    """`theme/id` -> the subject, as the series wrote it."""
    out = {}
    for theme, lst in (series.get("themes") or {}).items():
        for s in lst or []:
            out[f"{theme}/{s['id']}"] = {**s, "theme": theme}
    return out


def xmp_packet(model: str, series: str) -> str:
    """The disclosure that travels inside the file: IPTC's code for model-generated media."""
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about=""'
        ' xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"'
        ' xmlns:xmp="http://ns.adobe.com/xap/1.0/">'
        f"<Iptc4xmpExt:DigitalSourceType>{IPTC_MARKER}</Iptc4xmpExt:DigitalSourceType>"
        f"<xmp:CreatorTool>caravan imagery, series {series}, model {model}</xmp:CreatorTool>"
        "</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end=\"w\"?>"
    )


def crop_box(w: int, h: int, aspect: str, focal: tuple[float, float]) -> tuple[int, int, int, int]:
    """The largest box of `aspect`, centred on the focal point, clamped to the edges."""
    ratio = ASPECTS[aspect]
    if w / h > ratio:
        cw, ch = round(h * ratio), h
    else:
        cw, ch = w, round(w / ratio)
    left = min(max(round(w * focal[0] - cw / 2), 0), w - cw)
    top = min(max(round(h * focal[1] - ch / 2), 0), h - ch)
    return left, top, left + cw, top + ch


def encode(im, width: int, xmp: str) -> bytes:
    """Descend the quality ladder until the file fits its cap; refuse if even the floor does not."""
    from PIL import Image

    height = round(width * im.height / im.width)
    scaled = im.resize((width, height), Image.Resampling.LANCZOS)
    for quality in QUALITIES:
        buf = io.BytesIO()
        scaled.save(buf, "WEBP", quality=quality, method=6, xmp=xmp)
        data = buf.getvalue()
        if len(data) <= BYTE_CAPS[width]:
            return data
    refuse(
        f"the {width} px derivative stays above {BYTE_CAPS[width]} bytes even at quality "
        f"{QUALITIES[-1]} ({len(data)} bytes)"
    )


def derivatives(png: Path, aspect: str, focal: tuple[float, float], xmp: str):
    from PIL import Image

    with Image.open(png) as raw:
        im = raw.convert("RGB")
        source = {"width": im.width, "height": im.height}
        im = im.crop(crop_box(im.width, im.height, aspect, focal))
        out = {w: encode(im, w, xmp) for w in WIDTHS}
    total = sum(len(b) for b in out.values())
    if total > AGGREGATE_CAP:
        refuse(
            f"the three derivatives come to {total} bytes, above the {AGGREGATE_CAP} an image may "
            f"have. That cap is one image's share of the site's 3,000,000 byte ceiling (FR-029); "
            f"raising it means choosing fewer widths or another format, not a bigger number"
        )
    return out, source, total


def candidates(images: list[dict], key: str, round_dir: Path) -> list[dict]:
    """The sheet's numbering, reproduced: present files only, in seed order, 1-indexed."""
    cands = [
        i for i in images
        if f"{i['theme']}/{i['subject']}" == key and (round_dir / i["file"]).exists()
    ]
    return sorted(cands, key=lambda i: i["seed"])


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_record(entry: dict, subject: dict, rid: str, focal, source, ders) -> dict:
    """The record, in the order contracts/image-record.schema.json states it."""
    alt = subject["alt"].strip()
    if not alt.endswith(ALT_SUFFIX):
        alt = f"{alt} {ALT_SUFFIX}"
    return {
        "id": rid,
        "series": entry["series"],
        "theme": entry["theme"],
        "subject": entry["subject"],
        "generation": {
            "model": entry["model"],
            "revision": entry["revision"],
            "model_licence": entry["model_licence"],
            "model_card": entry["model_card"],
            "pipeline": entry["pipeline"],
            "prompt": entry["prompt"],
            "negative_prompt": entry.get("negative_prompt", ""),
            "seed": entry["seed"],
            "steps": entry["steps"],
            "guidance": entry["guidance"],
            "width": entry["width"],
            "height": entry["height"],
            "generated": entry["generated"],
            "hardware": entry["hardware"],
            "generator": {
                "commit": entry["generator"]["commit"],
                "image_digest": entry["generator"]["image_digest"],
                "script_sha256": entry["generator"]["script_sha256"],
            },
        },
        "licence": LICENCE,
        "placements": [subject["placement"]],
        "scene": subject["scene"].strip(),
        "alt": alt,
        "focal_point": [focal[0], focal[1]],
        "aspect": subject["aspect"],
        "source": {**source, "sha256": subject["_source_sha"]},
        "derivatives": {
            str(w): {"file": f"{rid}-{w}.webp", "bytes": len(b), "sha256": sha256(b)}
            for w, b in ders.items()
        },
    }


def write_credits() -> int:
    """Rewritten from the records on every placement, so it cannot drift from them (FR-033)."""
    import yaml

    records = []
    for d in sorted(p for p in IMAGES.iterdir() if p.is_dir()) if IMAGES.exists() else []:
        f = d / "image.yaml"
        if f.exists():
            records.append(yaml.safe_load(f.read_text(encoding="utf-8")))
    if not records:
        # The footer links this page from every page in the site (FR-034), so it has to exist
        # before the first image is placed or the build fails on an unknown document. It says the
        # true thing in the meantime.
        CREDITS.write_text(
            f"""---
orphan: true
---

# Image credits

Every picture on this site is {DISCLOSURE}: drawn by a diffusion model from a written prompt, not
photographed and not fetched from anywhere. None of them shows real hardware.

No generated image is placed on the site yet. When one is, this page will name it, the model that
made it, that model's licence, the day it was made and the class of machine it ran on.

*This page is written by `scripts/imagery/place.py` from the records under
`docs/_static/images/`. Do not edit it by hand.*
""",
            encoding="utf-8",
        )
        return 0
    intro = f"""---
orphan: true
---

# Image credits

Every picture on this site is {DISCLOSURE}: drawn by a diffusion model from a written prompt, not
photographed and not fetched from anywhere. None of them shows real hardware. Each one below names
the model that made it, that model's licence, the day it was made and the class of machine it ran
on. The full recipe — prompt, seed, step count, container digest — sits beside the image itself,
in its `image.yaml`.

The images themselves are [{LICENCE}]({LICENCE_DEED}): no rights reserved, no attribution
required.

*This page is written by `scripts/imagery/place.py` from the records. Do not edit it by hand;
place an image and it is rewritten.*
"""
    lines = intro.split("\n")
    for r in records:
        g = r["generation"]
        used = ", ".join(r["placements"])
        lines += [
            f"## {r['scene']}",
            "",
            f"```{{image}} /_static/images/{r['id']}/{r['derivatives']['960']['file']}",
            f":alt: {r['alt']}",
            ":width: 480px",
            "```",
            "",
            f"{DISCLOSURE} with [{g['model']}]({g['model_card']}) ({g['model_licence']}) on the "
            f"project's own hardware ({g['hardware']}), {g['generated']}.",
            "",
            *([f"- **Made for**: the [Mobility Model Zoo](https://github.com/mhabedank/mobility-model-zoo),"
               f" and used here with its record"] if r.get("origin") else []),
            f"- **Used on**: {used}",
            f"- **Licence**: [{r['licence']}]({LICENCE_DEED})",
            f"- **Record**: `docs/_static/images/{r['id']}/image.yaml`",
            "",
        ]
    CREDITS.write_text("\n".join(lines), encoding="utf-8")
    return len(records)


def main(argv: list[str] | None = None) -> int:
    import yaml

    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("round", type=Path, help="the round directory (images + manifest.json)")
    ap.add_argument("--picks", required=True, type=Path, help="picks.yaml from the contact sheet")
    ap.add_argument("--series", type=Path, default=Path(__file__).parent / "series/siebdruck.yaml")
    ap.add_argument("--only", default="", help="place one theme/subject rather than every pick")
    ap.add_argument("--focal", default="0.5,0.5", help='crop centre as "x,y" fractions')
    ap.add_argument("--id", default="", help="record id (default: <theme>-<subject>)")
    ap.add_argument("--dry-run", action="store_true", help="report and write nothing")
    a = ap.parse_args(argv)

    manifest_path = a.round / "manifest.json"
    if not manifest_path.exists():
        refuse(f"no manifest.json in {a.round} — an image without provenance is not placed")
    images = json.loads(manifest_path.read_text(encoding="utf-8")).get("images", [])
    picks = (yaml.safe_load(a.picks.read_text(encoding="utf-8")) or {}).get("picks") or {}
    subjects = subject_map(load_series(a.series))

    fallback_focal = tuple(float(x) for x in a.focal.split(","))
    placed = 0
    for key, choice in picks.items():
        if a.only and key != a.only:
            continue
        if choice == "none" or choice is None:
            print(f"{key}: none — left for another round")
            continue
        subject = subjects.get(key)
        if subject is None:
            refuse(f"{key} is in {a.picks.name} but not in the series")
        if not subject.get("alt") or not subject.get("scene"):
            refuse(f"{key} has no {'alt' if not subject.get('alt') else 'scene'} in the series")

        cands = candidates(images, key, a.round)
        if not 1 <= int(choice) <= len(cands):
            refuse(f"{key}: candidate {choice} does not exist ({len(cands)} rendered)")
        entry = cands[int(choice) - 1]
        png = a.round / entry["file"]
        # FR-019, the rule the provenance chain rests on.
        missing = [f for f in REQUIRED_PROVENANCE if entry.get(f) in (None, "")]
        missing += [
            f"generator.{f}" for f in REQUIRED_GENERATOR
            if not (entry.get("generator") or {}).get(f)
        ]
        if missing:
            refuse(
                f"{entry['file']} has an entry in {manifest_path.name} but it carries no "
                f"{', '.join(missing)} — that is not provenance, and an image whose recipe is "
                f"incomplete is not traceable to the run that made it"
            )

        rid = a.id or f"{entry['theme']}-{entry['subject']}"
        target = IMAGES / rid
        if target.exists():
            refuse(f"{target.relative_to(REPO)} exists; remove it first")

        # the series may carry its own focal point; the flag is the fallback
        focal = tuple(subject.get("focal") or fallback_focal)
        subject = {**subject, "_source_sha": sha256(png.read_bytes())}
        xmp = xmp_packet(entry["model"], entry["series"])
        ders, source, total = derivatives(png, subject["aspect"], focal, xmp)
        record = build_record(entry, subject, rid, focal, source, ders)

        share = 100 * total / AGGREGATE_CAP
        print(f"{key}: #{choice} seed {entry['seed']} -> {rid}  {total:,} B ({share:.0f}% of cap)")
        if a.dry_run:
            continue
        target.mkdir(parents=True)
        for w, data in ders.items():
            (target / f"{rid}-{w}.webp").write_bytes(data)
        (target / "image.yaml").write_text(
            yaml.dump(record, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8"
        )
        placed += 1

    if placed and not a.dry_run:
        n = write_credits()
        print(f"placed {placed}; docs/credits.md rewritten from {n} records")
    elif a.dry_run:
        print("dry run — nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
