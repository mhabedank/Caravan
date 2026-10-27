# The site's design language

Not a published page. `exclude_patterns` keeps `docs/design/` out of the site; this is the record a
later page is made to match, so that matching does not mean guessing (FR-031).

The identity is the Mobility Model Zoo's, copied on 2026-10-27 (feature 010, D1). Caravan must not
depend on the zoo, so it is a copy: no shared package, no submodule, nothing fetched at build time.
**The two may drift and nothing keeps them in step.** A later divergence is not a defect, and a
change here is not owed to the zoo.

## The one rule above the others

**Legibility wins.** Where the identity and legibility disagree, legibility takes it, and this
sentence is the authority for saying so in a review (FR-032). The identity is a register, not a
costume: it is there because flat ink and hard edges suit a project about models that must fit, not
because it is a style we like.

## What Caravan changed, and all it changed

Three things, because D4 asks that Caravan read as the zoo's sibling and not its twin:

1. **Its own mark** — three squares of decreasing size on a line. A caravan is a sequence moving
   along a route, and a model that reaches a board has been made smaller twice. It uses the ground
   and the ink only, never the accent, which keeps the reservation below absolute.
2. **Its own reservation for the accent** — below.
3. **Syntax colour from the identity's inks**, which the zoo had no need of.

## Colour

Four inks, shared by both schemes because a printed surface does not turn over: navy `#062544`,
cream `#FBEED0`, mint `#A5DBC6`, orange `#ED9B20`. The interface's neutrals are defined per scheme,
both worked out rather than one derived from the other.

**Every interface colour is declared in `tokens.css` and nowhere else**, including the parts that
are dark in both schemes. A change of identity is then an edit to one file. `site.css` contains no
colour literal, and the site serves no third-party stylesheet: Sphinx's own `pygments.css` is not
linked, because its fifty-odd literals are colours the identity does not have (`docs/_ext/identity.py`).

The one exception, and why it is one: `mark.svg` and `favicon.svg` carry literal values as
fallbacks after their `var()`, because an icon is rendered outside the document and gets no
stylesheet. The zoo's own mark does the same.

### The accent is reserved

**In the interface: the budget and its verdict.** A figure that must fit, and the gate's answer
about whether it did. Nothing else in the interface may use it — not a call to action, not an
emphasis, not a heading. `--accent-use` exists so a check can find violations; `.budget` and
`.verdict` are the only classes that may read it.

**In an illustration: the subject of the picture.** The board in the hero, the board in leg 3's
motif, the bar that stops the model in leg 4's. This half of the rule was added after the first
finished page was looked at beside the zoo's. The zoo reserves its warm ink for the vehicle or the
machine — the thing a picture is *about* — and reserving it everywhere, including in the drawings,
made this site duller than the one it was copied from for a rule no reader could see.

The two halves do not fight: in an interface the warm ink means "this is the number that decides",
and in a drawing it means "this is the thing the drawing is about". What stays banned is the
middle, where a button or a heading wears it for emphasis and the reservation stops meaning
anything.

### Contrast, measured

Computed from `tokens.css` on 2026-10-27. AA wants 4.5:1 for body text and 3:1 for a border or a
focus ring. These are the figures, not the intentions:

| Pair | Light | Dark |
|---|---|---|
| text on background | 13.74:1 | 15.28:1 |
| text on surface | 15.09:1 | 13.74:1 |
| text on a code block | 12.52:1 | 15.28:1 |
| muted text on background | 6.94:1 | 8.01:1 |
| muted text on surface | 7.62:1 | 7.21:1 |
| link on background | 8.36:1 | 9.51:1 |
| link on surface | 9.18:1 | 8.55:1 |
| text on the accent | 13.74:1 | 6.87:1 |
| strong border on background | 3.44:1 | 5.03:1 |
| focus ring on background | 4.88:1 | 7.64:1 |

The lowest figure in the set is the strong border at 3.44:1, which clears its 3:1 and is the one to
watch if a neutral is ever adjusted.

**This table is a snapshot, and it is not the check.** It lists the interface's pairs, and a page is
made of more pairs than an interface. The first run of the browser audit proved it: strings in code
blocks were set in `--s-b`, which is 2.97:1 against the code background in the light scheme and
fails AA — an ink and a surface that both appear in this table, in a combination that does not.
Strings are `--gain-ink` now, 6.23:1 and 10.14:1. The audit is the check (FR-034); this table is
for choosing.

## Type

Two faces, copied with their OFL-1.1 notice: **Archivo**, a grotesque with a width axis, and
**JetBrains Mono**. Headlines are set narrow over the width axis; body copy stays at full width.
Body text is 17px at 1.6 line height, 16px below 560px.

| Role | Size | Weight | Width |
|---|---|---|---|
| the hero's headline | `clamp(31px, 3.4vw, 45px)` | 700 | 80% |
| a band's heading (landing h2) | `clamp(27px, 3.3vw, 36px)` | 700 | 82% |
| an article's h1 | `clamp(30px, 4vw, 38px)` | 700 | 80% |
| an article's h2 | `clamp(24px, 3vw, 30px)` | 700 | 82% |
| h3 | 22px (21px in a card, 19px in a band of three) | 650–700 | normal |
| h4–h6 | 18px | 650 | normal |
| lead | 20px, 17.5px in the hero | normal | normal |
| body | 17px | normal | normal |
| caption | 13px, muted | normal | normal |
| eyebrow | 13px, uppercase, tracked | 650 | normal |

The hero's headline is clamped to what its panel can hold, and sets `hyphens: none`: at the size
the panel first wanted, "microcontroller" hyphenated, and the first screen of the site read
"A CSV goes in. A model your mi-crocontroller runs comes out." A last-resort `overflow-wrap` is
kept for a reader at 200% zoom, where a break is better than a page that scrolls sideways.

Measure is capped at 720px for an article (`.prose`) and per element on the landing page, which is
not an article. Sphinx writes plain headings, so the scale is attached to real headings; the
utility classes the zoo's stylesheet carries for a generator that writes `<h2 class="h2">` are not
here, because nothing on this site uses them.

## Code, tables, figures

- **Code** wraps rather than scrolling sideways, because FR-035 forbids a sideways scroll at phone
  width and a wrapped command is still readable. 14px, 1.7 line height, in a bordered block.
- **Syntax colour** makes four distinctions and no more: a comment recedes to muted and italic, a
  string takes the mint, a keyword takes the blue, everything else is body text. A fuller palette
  would need inks the identity does not have.
- **Tables** are for scanning across columns, never for carrying an explanation (FR-038). Below
  861px a table scrolls inside its own frame rather than pushing the page sideways.
- **Figures** are flat: colour fields, hard edges, no gradient and no shadow. Borders do the work
  shadows would.
- **Meaning is never carried by colour alone** (FR-036). Where a label means something, a border
  style carries it too: the provenance labels are dotted for `estimated`, dashed for `emulated`,
  solid for `measured`, so they survive a monochrome print and a reader who cannot separate the
  inks. This is the zoo's own technique, borrowed.

## The landing page

It is the one page that is not an article, and it is built from bands rather than from prose.

- **The first screen is a poster**: a navy panel of text hard against a full-bleed illustration,
  with an eyebrow above the headline and two calls to action below it. The words come from
  `index.md`'s own front matter (`eyebrow`, `tagline`, `lead`), so changing them is still an edit
  to the page; only the shape is in the theme.
- **Below it, bands.** Each `##` is a band that runs to both edges of the window and sets its own
  gutter, which is what lets alternate bands carry a background. The measure is restored per
  element, not per page: a paragraph is capped, a grid of three is not.
- **Every heading is a real heading.** The first draft built the grids out of `container`
  directives, and docutils renders a heading inside one as `<p class="rubric">`: the page looked
  right and had no structure under it. The grids are built from the sections instead, with
  `attrs_block` putting the class on the section (`{.band .band-3}` above the `##`).
- **The route's four cards carry a motif** — a flat drawing of what that leg is about. They are
  backgrounds, not `<img>`s, because the card already says in words what the leg is and a reader
  on a screen reader should not hear it twice.

The whole landing page is a deliberate second pass. The first one copied the identity's tokens but
not its compositions, and the result was a documentation page wearing the zoo's colours — exactly
the half step the zoo's own identity work warns against. Copying a design language means copying
the shapes it makes, not only the inks it makes them with.

## The words

The verbal register is the journey the project's name already implies.

- The series is **the route**. Its parts are **legs**, numbered. A leg's title names what the reader
  ends with, so a title read on its own says what the leg is worth.
- **"Stage"** is reserved for the pipeline's own stages — data, build, train, quantize, export. A
  leg is not a stage and a stage is not a leg; the collision is the reason "leg" was chosen.
- What a board can hold is its **budget**, and the gate's answer is its **verdict**.
- Address the reader as "you". Prefer the concrete noun to the abstraction: "the file the firmware
  compiles", not "the deliverable".
- No exclamation marks, and never tell the reader a task is simple: no "simply", no "just do", no
  "easy to". A thing is short or it is not; saying it is easy does not make it so, and a reader who
  finds it hard has been told they are slow.

  The rule is about the *reader's* effort, not the word. "Easy to miss until it bites" and "easy to
  misread" are warnings — they say the opposite of "this is easy" — and they stay. That distinction
  was found by auditing the pages against an earlier version of this line, which banned the word
  outright and flagged two sentences that were doing the right thing.
- Say the cost before the benefit is claimed, not after.

## What a page owes the reader

- A heading structure in order, with no level skipped. **The build checks this**, and it very
  nearly did not: the landing page's h1 is shown in the theme, and the first attempt wrote the page
  with no title at all, which made MyST report every page and was "fixed" by silencing the report —
  along with the check that had caught the manifest reference skipping H2 to H4 forty-three times.
  The page keeps its title in the source now and the extension drops the duplicate, so nothing is
  suppressed. The lesson is worth more than the rule: a warning that fires on something correct is
  a reason to look at the source, not at the warning list.
- Every abbreviation expanded at its first use on that page (FR-018).
- Every figure about hardware carrying exactly one provenance label (Principle IV).
- A text alternative for every image, and the page still complete with images unavailable (FR-037).
- Nothing clipped and nothing scrolling sideways at phone width or 200% zoom (FR-035).
