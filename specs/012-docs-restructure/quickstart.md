# Quickstart: verifying the documentation restructure

Everything here runs on an ordinary machine: the site's build tools, a browser, and the existing
checks. Nothing needs the GPU or a board.

## Build it strictly

```bash
uv run --group docs sphinx-build -W -b html docs _site
```

**Expect**: no output and exit 0. With `nitpicky = True` in `conf.py`, this one command is the check
for FR-014: an unknown field, command, rule, board or glossary term is an error naming the page and
the name. To see it refuse, put `` {mf}`export.nope` `` on any page and build again — expect
`'mf' reference target not found: export.nope` and a non-zero exit.

## Story 1 — one page to find the way in

Serve `_site` and open any page.

- The header has exactly **Documentation** and **Search** (FR-001).
- **Documentation** opens `contents.html`, which reads, top to bottom: First steps (From scratch:
  Caravan at a glance, Installation; Tutorial: parts 1–4), Getting help, How the documentation is
  organized, then the five layers and the project (FR-002, FR-003).
- From it, each layer's reference is one click (SC-001). Count the clicks to `ref/cli` and
  `ref/manifest/index`: two from any page, one from the landing page's own buttons.

## Story 2 — one field, fast

Pick ten fields, e.g. `export.targets`, `preprocessing.window_size`, `trainer.epochs`. From the
overview, reach each entry in at most two clicks (SC-002): Documentation → Manifest reference →
the section page. Each entry shows type and default on its first line.

**Old links still land** (FR-010). In a browser, open:

- `reference/manifest.html#preprocessing` → the preprocessing section page;
- `reference/cli.html#caravan-export` → the `caravan export` entry;
- `reference/rules.html#v-1` → the `V-1` entry;
- `route/1-first-model.html` → tutorial part 1.

Each must end at the entry itself, not the top of a page. A headless browser checks the final
address after the script has run:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --dump-dom "http://127.0.0.1:8000/reference/cli.html#caravan-export" | grep -c 'id="cli-caravan-export"'
```

## Story 3 — names are links

Open tutorial part 2. `export.targets`, `caravan export` and the first "gate" in a section are
links; the second "gate" in the same section is not (FR-012, FR-016). Open the generated index
(`genindex.html`): every field, command, rule and board is listed with its kind (FR-013).

The existing reference check proves every object the code defines has an entry (SC-003):

```bash
uv run --group dev --group docs pytest -q tests/contract/test_docs_reference.py
```

## Story 4 — from scratch

`intro/overview.html` carries one manifest through every stage, with a link per stage, and says
what Caravan is for and what it leaves out. `intro/install.html` lists what a reader needs and ends
with one command that proves the install. Part 1 links to it instead of repeating it.

## Story 5 — boxes and sequences

Every tutorial part and topic guide opens with one "You will learn" box — on a tutorial part, with
its minutes and what you end with — and ends with previous/next links inside its own sequence
(FR-018, FR-019). Check the edges: part 4's "next" does not jump to a topic guide, and the first
topic guide's "previous" is not a tutorial part. Toggle the colour scheme: note, warning, see also
and learn boxes stay distinct and legible in both (FR-017).

## Story 6 — the how-to guides

Follow `howto/add-a-board` with a datasheet: the new board is listed by `caravan boards` and accepted
by `caravan validate` in `export.targets`. Follow `howto/choose-a-budget`: it ends with an
`accuracy_drop_max` taken from a run's own figures.

## The metaphor and the language

```bash
grep -rniE "\broute\b|\blegs?\b|half hour" docs --include=*.md | grep -v "_static/\|releases/"
grep -rniE "\broute\b|\blegs?\b" README.md examples/
grep -rniE "\babout [0-9]+ minutes|from the start of|roughly|should be fine" docs --include=*.md
```

**Expect**: nothing from either, outside release notes that record history (FR-022, FR-024). Then
read the landing page: it ends after the tutorial cards (FR-025).

## Nothing else grew

```bash
git diff --stat main -- pyproject.toml uv.lock     # nothing (FR-026)
git diff -M --diff-filter=A --name-only main -- tests | wc -l   # 0: renames are not new files (FR-027)
uv run --group dev --group docs pytest -q tests/contract/ tests/integration/test_readme.py
```

The documentation job in CI stays under ten minutes (FR-028); it prints its own duration.
