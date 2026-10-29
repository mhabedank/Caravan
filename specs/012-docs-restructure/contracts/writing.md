# Contract: writing

The pages are product pages (FR-022). This is the rule a reviewer checks them against.

## No hedging

A statement says what is true, plainly, once. Removed wherever they appear:

- cumulative or conditional time: "about 10 minutes, 15 from the start of leg 1", "with the install
  already done", "after the half hour";
- softeners in place of a fact: "about", "roughly", "should", "generally", "in most cases";
- apologies and meta-commentary: "nothing here has been tested in…", "the page says so rather than
  pretending otherwise", "worth knowing rather than hiding";
- a limit repeated as a caveat. A limit the reader needs is stated once, as a fact, where it
  applies: "Training needs Python 3.13."

Kept, because they are facts and not hedges:

- the `estimated` / `emulated` / `measured` label on a number about hardware (Principle IV);
- what is verified and what is not, stated plainly in the reference ("compiles; not yet run on a
  board"), never inflated in a tutorial (FR-023).

## No route, no legs

The tutorial is a tutorial, in parts: "Part 1: Your first model". No page, heading, label, button
or address uses "route", "leg" or "the half hour" (FR-024).

## Linking

- The first use of a glossary term in each `##` section links with `{term}`; later uses do not.
- Every manifest field, command, rule and board named in running text links with its role
  (`{mf}`, `{cmd}`, `{rule}`, `{board}`), every time it is named as an object — an object role is
  short and reads as the name.
- Headings never carry links; code blocks never do.
- A plain link is for a page; a role is for a thing on a page.

## Boxes

| Box | Syntax | When |
|---|---|---|
| note | `:::{note}` | a fact the reader needs beside the text |
| warning | `:::{warning}` | something that fails or loses work if ignored |
| see also | `:::{seealso}` | where to read on; every topic guide ends with one (FR-020) |
| you will learn | `:::{admonition} You will learn` + `:class: learn` | top of every tutorial part and topic guide (FR-018) |

A tutorial part's learn box also states its minutes and what the reader ends with (research R11).
No page opens with two boxes.
