# Phase 0 research: a website that teaches Caravan in half an hour

Eight unknowns stood between the spec and a plan. Each is settled below with what was actually
checked, not with a preference.

## R1 — Does the zoo's identity port to Sphinx, or does the generator have to change?

**Decision: it ports. Sphinx keeps the site, and the identity arrives as a theme of the project's
own.**

What was checked. The zoo's site is not Sphinx — it is a generator of its own
(`src/mobility_model_zoo/site/`, Jinja templates plus modules for motifs, cards, charts and
checks). But **Sphinx's own templating is Jinja2**, and the zoo's `base.html.j2` is ordinary Jinja
with one context object (`site.*`) and blocks for title, description and main. Its markup is a
header, a skip link, `main#main`, a footer, and the wrappers `site.css` targets (`.wrap`, `.hd`,
`.brand`, `.nav`, `.prose`, `.sec`, `.stack`). Nothing in it depends on the zoo's Python.

`site.css` is 357 lines and `tokens.css` 92. Reading the selectors, the file is element rules plus
utility classes — `.prose > * + *`, `.h1`, `.lead`, `.muted`, `.cap`, `.wrap` — not rules bound to
the zoo's page shapes. That is the layer Sphinx needs anyway, because Sphinx hands the theme one
body of HTML to wrap.

So the port is: `tokens.css` verbatim; `site.css` with its selectors mapped onto the classes
Sphinx emits for body content; `base.html.j2` becoming the theme's `layout.html`, with `site.*`
replaced by Sphinx's context and the navigation built from the table of contents.

**Rationale.** A theme of our own adds **no dependency at all** — templates and static files under
`docs/`, nothing to install — which Principle XII prefers over pulling in a third-party theme.
It also gives exact control of the markup, which is what makes the copied CSS land cleanly rather
than fighting a theme's own opinions.

**Verified, not assumed.** A minimal theme of this shape was built against the pinned Sphinx
(9.2.0) before this plan was written: `docs/_themes/caravan/` with `theme.conf` inheriting `basic`,
a `layout.html` carrying the zoo's markup, and a stylesheet. It built, the markup came out as
written — the skip link, `.hd`, `.brand`, `main#main`, `.wrap.prose` — the stylesheet was linked and
the page body rendered inside it. The only warnings were missing pages from the partial copy used
for the trial; none came from the theme.

One stumbling block found by doing it, recorded so the implementation does not lose time to it: the
stylesheet loop must be `{% for css in css_files %}` with `pathto(css.filename, 1)`. The older idiom
`pathto(css, 1)` fails on this version, because `css_files` now holds stylesheet objects rather than
strings, and the build dies with a theme error that names neither the template nor the line.

**Alternatives considered.** *Re-skinning an existing dark-mode-capable theme* was rejected: every
such theme carries its own design decisions, so the work becomes overriding someone else's CSS with
the zoo's, and the result is two design systems in conflict — the exact failure the zoo recorded in
its own identity feature. *Adopting the zoo's generator* was rejected: it would mean copying a large
body of Python (the constitution forbids depending on the zoo, so it could only be a copy), losing
Sphinx's ordered navigation, anchors and warnings-as-errors, and inheriting a tool built for a model
catalogue rather than for an ordered series of lessons.

## R2 — What does the deployment leg actually run on, and how much has to be built?

**Decision: a second PlatformIO project, `examples/esp32/`, generic and serial-only, derived from
the firmware that already exists.**

What was checked. The withdrawn board is itself an ESP32, so `examples/lora32/` is already a
working ESP32 + TensorFlow Lite Micro firmware built with PlatformIO and ESP-IDF. Its 464 lines
divide cleanly: `main.cc` (198 lines) is the inference and the comparison against the host's
answers, and `oled.cc`, `oled.h`, `font5x7.h`, `board_pins.h` (266 lines) are the display. The
reader's own work is four generated files copied into `src/model/` — `model_data.h`,
`model_data.cc`, `resolver.h`, `test_windows.h`.

The generic project is therefore `main.cc` with the display calls replaced by serial output, plus
the four build files, targeting PlatformIO's `esp32dev`. No new firmware technique is needed.

**Rationale.** D2 keeps `examples/lora32/` in the repository, so the generic path cannot be made by
converting it. A separate project costs a copy of `main.cc` that can drift; the mitigation is that
both are built in continuous integration (R3), which is where drift surfaces.

**Alternatives considered.** *One project with several PlatformIO environments* was rejected:
cheaper in lines, but the reader is sent into a directory whose configuration names the withdrawn
board, which FR-039 exists to prevent. *Using the generated `runner/<board>/main.cc`* was rejected
as the leg's starting point: the export calls it a starting point, the existing example does not
use it, and a thirty-minute promise cannot rest on something unproven. It stays what it is — a
skeleton for a reader building their own firmware.

## R3 — Which check closes the verification gap FR-042 names?

**Decision: the existing firmware workflow gains the generic project, and keeps blocking the
release.**

What was checked. `.github/workflows/firmware.yml` already does exactly what FR-042 asks, for the
wrong board: it exports the example, executes the guide's own command blocks (`board-tools`,
`board-copy`, `board-build`) as written, builds the firmware, and is called by the release workflow
before anything is published, so a firmware that does not build blocks the release. It also records
the linker's figures into the run summary, labeled as not measured on a board.

So the gap closes by adding the generic project's build and the deployment leg's blocks to that
workflow, next to the ones already there. The owner's board keeps its build; the documented path
gains one.

**Rationale.** The machinery, the toolchain cache (about 540 MB cold) and the release gate all
exist. Nothing new has to be invented, and the check exercises the same commands the leg tells a
reader to run, which is what FR-042 requires.

## R4 — What is Caravan's single warm accent reserved for?

**Decision: the budget and its verdict — a figure that must fit, and the gate's answer about
whether it did. Nothing else on the site may use it.**

What was checked. The zoo reserves its one warm orange for the vehicle or the machine: the subject
of the picture. Caravan's pictures have no vehicles. The candidates were the board and the budget.

**Rationale.** The budget is what Caravan is *about* — the constitution's Principle V is that
budgets are gates and not warnings, and the one thing a reader must take away is that a model
either fits or the run stops. Reserving the accent for the number and the verdict puts the project's
argument in its colour, and it differs from the zoo's reservation, which is what D4 asks for.

**Alternatives considered.** *The board* was rejected as too close to the zoo's own choice — the
board is the machine, so the two sites would reserve their accent for the same kind of thing and
read as one project. **This is the plan's proposal and the owner's to overrule**: it is a
judgement about meaning, not a finding.

## R5 — How many legs, and where do the two promises fall?

**Decision: four legs; the fifteen-minute mark at the end of leg 2, the thirty-minute mark at the
end of leg 3, and leg 4 beyond both.**

| Leg | About | Ends with | Cumulative |
|---|---|---|---|
| 1 | The example, run end to end | An int8 model and its C array exist, and the reader has seen the gate pass | ~5 min |
| 2 | The reader's own columns | A model that reads their data, with their own accuracy figure | **~15 min** |
| 3 | Onto an ESP32 | The board answers test windows, agreeing with the host | **~30 min** |
| 4 | Tightening the budget until the gate refuses | The per-layer table read, and a budget the reader chose | beyond |

**Rationale.** The spec requires an int8 model by fifteen minutes and hardware by thirty (FR-012),
and each leg to end in something countable (FR-010). Leg 1 must be the example rather than the
reader's data, because only a known dataset finishes in minutes. Leg 4 exists because a failing
gate is the most likely thing to happen to a reader's own data (FR-016) and the spec requires it to
be taught rather than survived; putting it last keeps it out of the promised half hour.

## R6 — How is "no dead addresses" met without a new dependency?

**Decision: the build writes a forwarding stub for every address that moves, from a redirect map in
the site's configuration.**

What was checked. Pages move: the single entry page becomes four legs, the board guide is removed,
and the own-project guide is folded into leg 2. The site is published as static files, so a forward
is an HTML file carrying a meta refresh and a canonical link. Sphinx has no built-in redirect, and
a small extension exists, but a redirect map plus a build hook is about fifteen lines and adds
nothing to install — which, under Principle XII, is the better trade for a site whose build tools
are pinned exactly.

**A tension this exposes, and how it is resolved.** FR-039 forbids the board's name on any page,
and FR-045 forbids dead addresses — but the board guide's address *contains* the board's name. The
forward is kept: it is marked `noindex`, appears in no navigation, carries no content about the
board, and forwards immediately to the deployment leg. FR-039 is about what a reader reads, and a
zero-second forward is not a page a reader reads.

## R7 — How is the accessibility claim measured, and what does it cost?

**Decision: a browser audit of every built page in both colour schemes, in the documentation
workflow, with the auditing library vendored.**

What was checked. The zoo does this already (`site/a11y.py`): Playwright drives headless Chromium,
a vendored copy of an auditing library is injected into each page, and every page is checked against
the A and AA levels in both colour schemes. Its own identity spec records *why*: the thresholds have
to be measured on the rendered page, because a palette table does not show where the defect appears.
This environment already has Playwright and Chromium installed.

Cost, stated rather than assumed: the browser is a few hundred megabytes in continuous integration
and the audit will take the documentation job from about a minute and a half to an estimated three
to four. The job runs only when documentation changes, and the browser is cacheable.

**Alternatives considered.** *Computing contrast from the tokens* was rejected because it is what
SC-012 explicitly refuses, and because it cannot see a real failure — text over an image, a focus
ring, a disabled control. *Running the audit only before a release* was rejected: a contrast defect
found at release time is found after the page was written, and the point of the check is to be cheap
enough to run while writing.

## R8 — Where does the landing page's layout come from?

**Decision: the theme carries a second layout, chosen by a field in the page's own front matter.**

What was checked. A landing page is the one page whose shape is not an article: no sidebar, a first
screen that has to answer in three seconds, and one primary next step. Sphinx renders every page
through the theme, and the content format already supports front matter, so a page can declare
which layout it wants and the theme can branch on it. The remaining pages keep the article layout.

**Rationale.** It keeps one generator, one build and one set of checks — the landing page is
inside the site's warnings-as-errors and inside the accessibility audit, rather than a hand-written
file beside it that no check would reach.

**Alternatives considered.** *A hand-written HTML landing page published next to the site* was
rejected for exactly that reason: it would be the most important page on the site and the only one
nothing verifies.
