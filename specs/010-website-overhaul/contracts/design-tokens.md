# Contract: the identity, as copied values

The identity is the Mobility Model Zoo's (D1). It arrives as a copy and never as a dependency
(FR-028): no shared package, no submodule, nothing fetched when the site is built. What follows is
the contract that makes that checkable.

## Origin, recorded once

The values come from the zoo's `tokens.css` as it stood on 2026-10-27. The origin is recorded in
the written design language, together with the statement that the two identities may drift and
that nothing keeps them in step. A later divergence is not a defect.

## The ink

Four inks, shared by both colour schemes, because a printed surface does not turn over: deep navy,
pale cream, pale mint, and one warm orange. The interface's own neutrals — background, surface,
text, muted text, border, link — are defined per scheme, both worked out rather than one derived
from the other.

The zoo's two iterations are inherited rather than repeated: the neutral ramp is half desaturated,
because at the ink's own saturation a whole page takes on a cast that a swatch does not show.

## What the accent is reserved for

**The budget and its verdict** (R4): a figure that must fit, and the gate's answer about whether it
did. Nothing else on the site may use it.

This is Caravan's own reservation, not the zoo's — the zoo reserves its accent for the vehicle or
the machine, and D4 asks that Caravan read as a sibling rather than a twin. It is the plan's
proposal, open to the owner's overrule, and it is recorded here so that a page using the accent for
emphasis fails a check rather than passing unnoticed.

## Type

Two typefaces, copied with their licence notice (OFL-1.1): a grotesque with a width axis, set
narrow for headlines, and a monospace for every command and every figure. Both are preloaded; body
text never uses a display setting.

## Rules that hold for the set

- No interface colour is defined outside the token set, including the parts that are dark in both
  schemes. A later change of identity is then an edit to tokens, not to pages.
- Both schemes are complete. The site honours the reader's system preference (FR-033).
- Contrast is a measurement, not an intention: every meaning-carrying pair is checked in a browser
  on the rendered page, in both schemes (FR-034, SC-012).
- Legibility wins over the identity wherever they conflict, and the written design language says so
  (FR-032).
- The interface and the figures come from one world; no second visual language is mixed in
  (FR-030). This is why the 8-bit register was dropped whole rather than kept for figures.

## What is checked

- No colour literal outside the token file.
- The accent appears only on what it is reserved for.
- Both schemes define every token the other defines.
- The browser audit passes at the A and AA levels on every page, in both schemes.
- The typefaces' notice is present beside them.
