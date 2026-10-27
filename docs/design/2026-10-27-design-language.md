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

**The budget and its verdict.** A figure that must fit, and the gate's answer about whether it did.
Nothing else on the site may use it — not a call to action, not an emphasis, not a heading.

The zoo reserves its warm ink for the vehicle or the machine, the subject of its pictures. Caravan
has no vehicles; it has budgets, and Principle V says budgets are gates and not warnings. Putting
the project's own argument in its one warm colour is the closest equivalent, and it keeps the two
sites apart at a glance.

`--accent-use` exists so a check can find violations. `.budget` and `.verdict` are the only classes
that may read it.

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
| display (the first screen only) | `clamp(34px, 5.4vw, 52px)` | 700 | 80% |
| h1 | `clamp(30px, 4vw, 38px)` | 700 | 80% |
| h2 | `clamp(24px, 3vw, 30px)` | 700 | 82% |
| h3 | 22px | 650 | normal |
| h4–h6 | 18px | 650 | normal |
| lead | 20px | normal | normal |
| body | 17px | normal | normal |
| small | 15px | normal | normal |
| caption | 13px, muted | normal | normal |
| eyebrow | 13px, uppercase, tracked | 650 | normal |

Measure is capped at 720px (`.prose`). Sphinx writes plain headings, so the scale is attached to
real headings inside `.prose`; the utility classes stay available for a page that sets one by hand.

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

- A heading structure in order, with no level skipped.
- Every abbreviation expanded at its first use on that page (FR-018).
- Every figure about hardware carrying exactly one provenance label (Principle IV).
- A text alternative for every image, and the page still complete with images unavailable (FR-037).
- Nothing clipped and nothing scrolling sideways at phone width or 200% zoom (FR-035).
