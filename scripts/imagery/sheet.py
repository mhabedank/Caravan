# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml>=6", "pillow>=11"]
# ///
"""The two pages the owner decides from: the subject sheet, and the contact sheet.

COPIED IN SHAPE from the Mobility Model Zoo's `sheet.html.j2` (its feature 019), on 2026-10-27:
the numbered candidates per subject, the click-to-pick, the picks kept in the browser and written
out as `picks.yaml`. The zoo's triage is NOT copied — there is no automatic rejection here, so the
sheet shows every candidate and the owner looks at all of them. At twenty subjects that is the
cheaper arrangement; at the zoo's hundred it is not, which is why the zoo built the other one.

Nothing here is part of the distribution. It is a PEP 723 script: `uv run --script` fetches its two
dependencies into a throwaway environment, and `pyproject.toml` is untouched.

    uv run --script scripts/imagery/sheet.py subjects scripts/imagery/series/siebdruck.yaml
    uv run --script scripts/imagery/sheet.py round ~/caravan-imagery/rounds/1

`subjects` is for before the GPU runs: twenty subjects, their prompts and what each is for, so the
prompts get fixed while fixing them is free. `round` is for after: the contact sheet.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

THUMB_WIDTH = 520

# The site's own inks, so the page the owner judges in is lit the way the site is. --pick and
# --none are the site's gain and pain pairs from tokens.css; the warm accent is deliberately absent,
# because the design language reserves it for the budget and its verdict (FR-026).
CSS = """
:root { color-scheme: light dark; --bg:#EFF2F0; --panel:#FCFCFB; --ink:#062544; --muted:#4B5450;
  --line:#CDD4CE; --none:#8A4310; --pick:#1C5E3F; }
@media (prefers-color-scheme: dark) { :root { --bg:#041C33; --panel:#062544; --ink:#EFF2F0;
  --muted:#A3B5AD; --line:#17496F; --pick:#9BD4A6; --none:#F5C07A; } }
* { box-sizing: border-box; }
body { margin:0; padding:28px 28px 120px; background:var(--bg); color:var(--ink);
  font:16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
h1 { font-size:26px; margin:0 0 6px; letter-spacing:-.02em; }
h2 { font-size:19px; margin:40px 0 4px; padding-top:18px; border-top:1px solid var(--line);
  text-transform:uppercase; letter-spacing:.09em; color:var(--muted); }
h3 { font-size:17px; margin:22px 0 2px; display:flex; align-items:center; gap:12px; flex-wrap:wrap; }
code { font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:13px; }
.muted { color:var(--muted); }
.placement { font-size:14px; color:var(--muted); margin:0 0 4px; }
.prompt { font-size:14px; line-height:1.5; color:var(--muted); margin:0 0 10px; max-width:104ch; }
.alt { font-size:13px; color:var(--muted); margin:6px 0 0; max-width:104ch; }
.row { display:flex; flex-wrap:wrap; gap:14px; }
figure { margin:0; width:520px; max-width:100%; cursor:pointer; border:3px solid transparent;
  border-radius:8px; background:var(--panel); }
figure.picked { border-color:var(--pick); }
figure img { display:block; width:100%; height:auto; border-radius:5px 5px 0 0; background:var(--line); }
figcaption { font-size:13px; padding:6px 10px; display:flex; justify-content:space-between; gap:10px; }
figcaption b { font-size:15px; color:var(--pick); }
figcaption a { color:var(--muted); }
button { font:inherit; font-size:14px; padding:5px 12px; border-radius:7px;
  border:1px solid var(--line); background:var(--panel); color:var(--ink); cursor:pointer; }
button.on, button.primary { background:var(--pick); color:var(--bg); border-color:var(--pick); font-weight:650; }
.subject { scroll-margin-top:20px; }
.subject.done h3 code { color:var(--pick); }
.subject.none h3 code { color:var(--none); }
.card { background:var(--panel); border:1px solid var(--line); border-radius:10px;
  padding:14px 18px; margin:14px 0; }
#bar { position:fixed; left:0; right:0; bottom:0; background:var(--panel);
  border-top:1px solid var(--line); padding:12px 28px; display:flex; gap:14px;
  align-items:center; flex-wrap:wrap; }
"""


def load_series(path: Path) -> dict:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def subjects(series: dict) -> list[dict]:
    out = []
    for theme, lst in (series.get("themes") or {}).items():
        for s in lst or []:
            out.append({**s, "theme": theme, "key": f"{theme}/{s['id']}"})
    return out


def esc(text: object) -> str:
    return html.escape(str(text if text is not None else ""))


def write_subjects(series_path: Path, out: Path) -> Path:
    """The page to read BEFORE rendering: what will be drawn, and what each picture is for."""
    series = load_series(series_path)
    subs = subjects(series)
    rows = []
    for theme in dict.fromkeys(s["theme"] for s in subs):
        rows.append(f"<h2>{esc(theme)}</h2>")
        for s in (x for x in subs if x["theme"] == theme):
            tag = ' <span class="muted">· reserve</span>' if s.get("reserve") else ""
            rows.append(
                f'<section class="subject"><h3><code>{esc(s["key"])}</code>'
                f'<span class="muted">{esc(s.get("aspect", "3:2"))}</span>{tag}</h3>'
                f'<p class="placement">for: {esc(s.get("placement", "—"))}</p>'
                f'<p class="prompt">{esc(s["prompt"])}</p>'
                f'<p class="alt">alt text: {esc(s.get("alt", ""))}</p></section>'
            )
    n_real = sum(1 for s in subs if not s.get("reserve"))
    body = f"""<h1>Subjects — series “{esc(series["name"])}”</h1>
<p class="muted">{n_real} subjects, {len(subs) - n_real} reserve. Every prompt below is sent as the
subject, followed by the series style. Read this before the render: changing a prompt here costs a
minute, changing it afterwards costs the whole round.</p>
<div class="card"><p class="prompt" style="margin:0"><b>style</b> — appended to every prompt:<br>
{esc(" ".join(series["style"].split()))}</p></div>
<div class="card"><p class="prompt" style="margin:0"><b>negative</b> — what the model is told to avoid:<br>
{esc(" ".join(series.get("negative", "").split()))}</p></div>
{"".join(rows)}"""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page(f"Subjects — {series['name']}", body), encoding="utf-8")
    return out


def thumbnails(round_dir: Path, images: list[dict]) -> Path:
    """One webp per candidate, because eighty full renders in one page is a page nobody opens."""
    from PIL import Image

    thumbs = round_dir / "thumbs"
    thumbs.mkdir(exist_ok=True)
    for img in images:
        src = round_dir / img["file"]
        dst = thumbs / (Path(img["file"]).stem + ".webp")
        if dst.exists() or not src.exists():
            continue
        with Image.open(src) as im:
            im = im.convert("RGB")
            h = round(im.height * THUMB_WIDTH / im.width)
            im.resize((THUMB_WIDTH, h), Image.LANCZOS).save(dst, "WEBP", quality=82, method=5)
    return thumbs


def write_round(round_dir: Path, series_path: Path | None) -> Path:
    manifest_path = round_dir / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"no manifest.json in {round_dir} — has the render run?")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    images = manifest.get("images", [])
    present = [i for i in images if (round_dir / i["file"]).exists()]
    thumbnails(round_dir, present)

    series = load_series(series_path) if series_path else None
    meta = {s["key"]: s for s in subjects(series)} if series else {}
    # Series order where we have it, manifest order otherwise, so a sheet is readable without one.
    order = list(meta) if meta else list(dict.fromkeys(f"{i['theme']}/{i['subject']}" for i in present))

    rows, pickable = [], 0
    for theme in dict.fromkeys(k.split("/", 1)[0] for k in order):
        rows.append(f"<h2>{esc(theme)}</h2>")
        for key in (k for k in order if k.startswith(theme + "/")):
            cands = [i for i in present if f"{i['theme']}/{i['subject']}" == key]
            cands.sort(key=lambda i: i["seed"])
            s = meta.get(key, {})
            figs = []
            for n, c in enumerate(cands, 1):
                stem = Path(c["file"]).stem
                figs.append(
                    f'<figure data-number="{n}"><img loading="lazy" src="thumbs/{esc(stem)}.webp" '
                    f'alt="{esc(key)} candidate {n}"><figcaption><span><b>#{n}</b> '
                    f'<span class="muted">seed {esc(c["seed"])}</span></span>'
                    f'<a href="{esc(c["file"])}" target="_blank" rel="noopener">full size</a>'
                    f"</figcaption></figure>"
                )
            none_btn = '<button type="button" class="none-btn">none of these</button>' if figs else ""
            if figs:
                pickable += 1
            missing = "" if figs else '<p class="muted">no candidate rendered.</p>'
            rows.append(
                f'<section class="subject" data-key="{esc(key)}"><h3><code>{esc(key)}</code>'
                f"{none_btn}<span class=\"state muted\"></span></h3>"
                + (f'<p class="placement">for: {esc(s["placement"])}</p>' if s.get("placement") else "")
                + (f'<p class="prompt">{esc(s["prompt"])}</p>' if s.get("prompt") else "")
                + f'<div class="row">{"".join(figs)}</div>{missing}</section>'
            )

    body = f"""<h1>Contact sheet</h1>
<p class="muted">{len(present)} candidates across {pickable} subjects, model
<code>{esc(manifest.get("model", "?"))}</code>. Click a picture to pick it for its subject, or
“none of these” when the subject needs another round. Picks are kept in this browser only —
download <code>picks.yaml</code> when you are done.</p>
{"".join(rows)}
<div id="bar"><span id="count"></span>
<button type="button" id="dl" class="primary">Download picks.yaml</button>
<button type="button" id="copy">Copy YAML</button>
<button type="button" id="clear">Clear</button></div>
<script>{SCRIPT}</script>"""
    out = round_dir / "sheet.html"
    out.write_text(page(f"Contact sheet — {round_dir.name}", body), encoding="utf-8")
    return out


SCRIPT = r"""
(function () {
  var key = "caravan-picks-" + location.pathname;
  var picks = {};
  try { picks = JSON.parse(localStorage.getItem(key) || "{}"); } catch (e) { picks = {}; }
  var sections = Array.prototype.slice.call(document.querySelectorAll("section.subject"));
  var pickable = sections.filter(function (s) { return s.querySelector("figure"); });
  function save() { try { localStorage.setItem(key, JSON.stringify(picks)); } catch (e) {} }
  function render() {
    var done = 0;
    sections.forEach(function (s) {
      var k = s.dataset.key, v = picks[k];
      s.classList.toggle("done", v !== undefined && v !== "none");
      s.classList.toggle("none", v === "none");
      s.querySelectorAll("figure").forEach(function (f) {
        f.classList.toggle("picked", String(v) === f.dataset.number);
      });
      var b = s.querySelector(".none-btn"); if (b) b.classList.toggle("on", v === "none");
      var st = s.querySelector(".state");
      if (st) st.textContent = v === undefined ? "" : (v === "none" ? "none" : "#" + v);
      if (v !== undefined) done++;
    });
    document.getElementById("count").textContent = done + " of " + pickable.length + " subjects decided";
  }
  function yaml() {
    var lines = ["picks:"];
    pickable.forEach(function (s) {
      var k = s.dataset.key;
      if (picks[k] !== undefined) lines.push("  " + k + ": " + picks[k]);
    });
    return lines.join("\n") + "\n";
  }
  sections.forEach(function (s) {
    var k = s.dataset.key;
    s.querySelectorAll("figure").forEach(function (f) {
      f.addEventListener("click", function (e) {
        if (e.target.tagName === "A") return;
        var n = Number(f.dataset.number);
        if (picks[k] === n) { delete picks[k]; } else { picks[k] = n; }
        save(); render();
      });
    });
    var b = s.querySelector(".none-btn");
    if (b) b.addEventListener("click", function () {
      if (picks[k] === "none") { delete picks[k]; } else { picks[k] = "none"; }
      save(); render();
    });
  });
  document.getElementById("dl").addEventListener("click", function () {
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([yaml()], { type: "text/yaml" }));
    a.download = "picks.yaml"; document.body.appendChild(a); a.click(); a.remove();
  });
  document.getElementById("copy").addEventListener("click", function () {
    navigator.clipboard.writeText(yaml());
  });
  document.getElementById("clear").addEventListener("click", function () {
    if (confirm("Clear every pick?")) { picks = {}; save(); render(); }
  });
  render();
})();
"""


def page(title: str, body: str) -> str:
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n{body}\n</body>\n</html>\n"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("subjects", help="the page to read before the render")
    p1.add_argument("series", type=Path)
    p1.add_argument("--out", type=Path, default=None)

    p2 = sub.add_parser("round", help="the contact sheet of a rendered round")
    p2.add_argument("round_dir", type=Path)
    p2.add_argument(
        "--series",
        type=Path,
        default=Path(__file__).parent / "series" / "siebdruck.yaml",
        help="for each subject's prompt and placement on the sheet; omit if it has moved",
    )

    a = ap.parse_args(argv)
    if a.cmd == "subjects":
        out = write_subjects(a.series, a.out or a.series.parent / "subjects.html")
    else:
        out = write_round(a.round_dir, a.series if a.series.exists() else None)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
