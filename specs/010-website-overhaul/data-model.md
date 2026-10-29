# Phase 1: the content model

The spec's entities are kinds of page and kinds of claim. They have no database; what they have are
fields a check can read, which is the point of writing them down. Each entity below names its
fields, the rules that hold for it, and the requirement it serves.

## Leg

One ordered part of the route. Four exist (R5).

| Field | Rule |
|---|---|
| `number` | 1 to 4, contiguous, the reader's own word for its position |
| `title` | Names what the reader ends with, not what the leg is about (FR-008) |
| `duration` | Stated before the first instruction, in minutes (FR-009) |
| `promise` | What will exist at the end, stated up front (FR-009) |
| `outcome` | The named, countable thing: a file, a figure, a verdict (FR-010) |
| `verification` | The command or observation by which the reader confirms the outcome themselves (FR-010) |
| `invalidates` | Which earlier results this leg's changes void, and the command that re-establishes them — legs 2 and 4 only (FR-015) |
| `dead_ends` | The known ways this leg fails, answered in place (FR-016) |
| `next` | The following leg and what it adds; absent on leg 4, which instead offers the way out (FR-013) |
| `exit` | What a reader who stops here still has (FR-011, FR-013) |

**Invariants.** A leg whose `outcome` cannot be verified by the reader is not a leg. No leg may
depend on a later leg to mean something. `duration` is cumulative to the promises: the end of leg 2
is the fifteen-minute mark, the end of leg 3 the thirty-minute mark (FR-012).

## Concept

One idea a reader must hold to make a choice. Lives once, linked from both the route and the
reference (FR-024).

| Field | Rule |
|---|---|
| `term` | The word as the manifest or the console spells it |
| `expansion` | What an abbreviation stands for, where it is one (FR-018) |
| `plain_definition` | One sentence assuming no machine-learning background (FR-018) |
| `why_it_exists` | What it is for, in the pipeline's terms |
| `how_to_choose` | Which value suits which data, for a concept that is a choice (FR-019) |
| `what_it_costs` | Memory, flash or accuracy, where the choice has a cost (FR-019) |
| `borrowed_from` | Named once where the term comes from another project's vocabulary (FR-025) |

**Invariants.** Every abbreviation appearing anywhere on the site resolves to a Concept with an
`expansion` and a `plain_definition`. A Concept is defined on exactly one page; other pages link to
it rather than restating it.

## Setting

One field a reader can write in the manifest. Enumerated from the schema, not by hand.

| Field | Rule |
|---|---|
| `path` | The manifest key, as a reader writes it |
| `facts` | Type, default, allowed values — kept scannable for lookup (FR-021) |
| `does` | What it changes about the model or the run (FR-020) |
| `why_default` | Why the default is the default (FR-020) |
| `when_to_change` | The situation that calls for another value (FR-020) |
| `at_the_extremes` | What goes wrong at each end of its range (FR-020) |
| `rules_in_words` | What each rule touching it rejects, and what to do instead — the identifier is at most an anchor, never the content (FR-022) |
| `read_by` | The stage whose result depends on it, kept from today's reference |

**Invariants.** Every setting the schema admits has all four prose fields; a setting with `facts`
alone fails a check. No `rules_in_words` consists of rule identifiers.

## Hardware claim

Any figure on the site about behaviour on a board. The constitution's Principle IV governs it and
this feature does not relax it.

| Field | Rule |
|---|---|
| `figure` | The number and its unit |
| `label` | Exactly one of `estimated`, `emulated`, `measured` (FR-006, SC-016) |
| `source` | Where it came from: for `estimated`, the method; for `measured`, the board, firmware, clock and toolchain |
| `board` | The board it is about |

**Invariants.** A figure without a `label` must not be rendered — on a marketing page as much as in
a reference table. No timing figure carries `measured` without a physical board behind it; the site
currently has no timing figure at all and gains none. A claim whose evidence is removed loses the
claim, not the label (FR-040, FR-044).

## Address

One published URL, before and after the overhaul (FR-045).

| Field | Rule |
|---|---|
| `old` | The address as published today |
| `new` | Where its content now lives, or `removed` |
| `forward` | Required whenever `old` differs from `new`; a stub carrying a meta refresh and a canonical link |
| `indexable` | `false` for every forward, so a stub never competes with the page it points at |

**Invariants.** No `old` address ends without either a page or a forward. A forward carries no
content of its own, which is what lets a forward from the withdrawn board's address exist without
breaching FR-039 (R6).

## Design token

One value of the copied identity (FR-026, FR-028).

| Field | Rule |
|---|---|
| `name` | The token's name, as the copied stylesheet spells it |
| `light` / `dark` | Its value in each colour scheme; both are worked out, neither derived from the other |
| `origin` | That it came from the zoo's identity, recorded once for the set rather than per token |
| `reserved_for` | Set on the accent alone: the budget and its verdict (R4) |

**Invariants.** No interface colour is defined outside the token set — the rule the zoo's own
identity feature arrived at, so that a later change of identity touches tokens rather than pages.
No value is fetched from the zoo at build time; the set is a copy (FR-028). The accent appears
nowhere but on what it is reserved for (FR-029).
