# Quickstart: validating the overhaul

How to confirm this feature works, from a clean checkout. Everything here runs locally with no
accounts and no keys, which is itself one of the things being checked (FR-051).

## Prerequisites

Python 3.13 and `uv`. The training framework is needed only for the step that executes the route
end to end; everything else runs without it. A browser for the accessibility audit is installed by
its own command, below.

## 1. The site builds, and nothing is broken

```bash
uv sync --python 3.13 --group docs
uv run --python 3.13 sphinx-build -W -b html docs _site
```

Expected: `build succeeded`. `-W` is what makes it a check — a broken link, a dead anchor or a page
no table of contents reaches fails the build (FR-046). Open `_site/index.html` to read the site
offline, which is the rest of FR-051.

## 2. The pages agree with the code

```bash
uv run --python 3.13 pytest -q tests/contract tests/unit/test_release_note.py tests/integration/test_readme.py
```

Expected: all pass. These are the checks in [contracts/checks.md](./contracts/checks.md) that need
no browser — the reference against the parser and the schema, every setting's prose, no unexplained
abbreviation, every published address still resolving, and the hygiene checks for the withdrawn
board and the internal artifacts.

A deliberate break should fail it. Add an unexplained abbreviation to any page, or a setting to the
schema without its prose, and re-run: the failure names the page and what is missing.

## 3. The accessibility claim, measured

```bash
uv sync --python 3.13 --group site-checks
uv run --python 3.13 python -m playwright install chromium
uv run --python 3.13 pytest -q tests/site/test_a11y.py
```

Expected: no violation at the A or AA level, on every page, in both colour schemes. This is the
check SC-012 asks for and the reason the claim is a measurement rather than an intention: it reads
the rendered page, so it sees text over an image and a focus ring, which a palette table cannot.

## 4. The route runs as written

```bash
uv venv --python 3.13 /tmp/route && VIRTUAL_ENV=/tmp/route uv pip install -e ".[train,verify]" pytest
VIRTUAL_ENV=/tmp/route /tmp/route/bin/python -m pytest -q tests/train/test_route_legs.py
```

Expected: every command the route gives a reader succeeds, the files each leg promises exist, and
the export step still fits on one screen. This is the heavy one — it trains — and it is why it lives
in the framework job rather than the documentation job.

## 5. The deployment leg's firmware compiles

```bash
VIRTUAL_ENV=/tmp/route /tmp/route/bin/caravan export examples/picket-mlp.yaml
cd examples/esp32 && pio run -e esp32dev
```

Expected: a built firmware, and the linker's RAM and flash figures in the output. Those figures are
`estimated` — the linker is not a board — and the site must say so wherever it repeats them
(Principle IV). This is the check that closes FR-042, and in continuous integration it runs before
every release.

## 6. The promises, measured over people

No command covers these. They are the feature's actual success criteria and they need readers
(SC-001 to SC-004):

- **Three seconds.** Show the first screen to at least five people who do not know the project, for
  five seconds, then take it away. Ask what Caravan produces and from what, what it refuses to do,
  and what the next step is. Pass is four of five on the first two and five of five on the third.
- **Fifteen minutes.** Five developers, clean machines, the install already done, a timer started at
  the first leg. Pass is four of five holding an int8 model inside fifteen minutes. Record whether
  the download weight was stated to them beforehand — the claim depends on it.
- **Thirty minutes.** The same runs continued on a generic ESP32, counting only those who had the
  board and its toolchain ready. Pass is four of five with the board answering inside thirty
  minutes of the same start.

- **The template choice.** Give five readers three described datasets and ask which model template
  each dataset calls for. Pass is four of five picking the template the site's own guidance implies.
  This is SC-009, and unlike the three above it tests whether the explanations work, not whether the
  route does.

Record each result with its date, the sample size and the machine, and note whether any reader
needed a source outside the site to finish a leg (SC-006). A promise measured once and not
written down is a promise the next change can break silently.

## What a reviewer should be able to confirm in ten minutes

1. The first screen answers what Caravan does, for whom, and what it costs — without scrolling.
2. Each leg states its duration and its promise before the first command, and ends with something
   the reader checks themselves.
3. `MLP` is expanded and explained, and the site says which template to pick for which data.
4. A manifest setting picked at random has all four kinds of prose, not just a table row.
5. Searching the built site for the withdrawn board's name, or for a spec directory or feature
   number, returns nothing.
6. Every figure about a board near it carries `estimated`, `emulated` or `measured`.
