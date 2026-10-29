# Phase 1 data model: Documentation organised like Django's

Five things the documentation is made of. None is stored outside the repository's files.

## Page

| Attribute | Values | Rule |
|---|---|---|
| address | path without suffix | Names its type: `intro/…`, `topics/…`, `ref/…`, `howto/…`; project pages keep theirs (FR-021) |
| type | tutorial · topic guide · reference guide · how-to guide · project | Exactly one (FR-005) |
| layer | manifest · pipeline & CLI · boards & targets · verification · exported model & firmware · project | Decides its place on the overview (FR-003) |
| sequence | `intro` · `topics` · `howto` · none | Previous/next stay inside it (FR-019, research R6) |
| learn box | present on tutorial parts and topic guides | 3–5 points (FR-018); on tutorial parts also the minutes and what you end with (R11) |

**Invariants**: no page title, heading, label, button or address uses the route-and-legs metaphor
(FR-024); every page is reachable from the overview within one click of its layer (SC-001).

## Reference object

| Attribute | Rule |
|---|---|
| kind | `manifest-field` · `cli` · `rule` · `board` |
| name | the field's dotted name (`export.targets`), the command (`caravan export`), the rule's code (`V-1`), the board's identifier (`esp32`) |
| entry | exactly one, on its reference page (FR-011) |
| anchor | `<kind>-<name>`, as Sphinx generates it (`manifest-field-export.targets`) |
| index entry | "name (kind)" in the generated index (FR-013) |

**Invariants**: every object the code defines has an entry, checked by the existing reference check
(SC-003); every mention in running text resolves, or the build fails (FR-014).

**Counts at the start**: 43 manifest fields, 8 commands, 52 rules, 3 boards.

**Counts at the end**: 51 manifest fields — the 43, plus the eight `defaults.<type>.*` fields, which
the parser knows and which had no entry of their own — 8 commands, 52 rules, 3 boards: 114 objects.

## Glossary term

| Attribute | Rule |
|---|---|
| term | a word or abbreviation, alphabetical |
| definition | one or two sentences (FR-015) |
| see | the topic guide that explains it, where one exists |

**Invariants**: at least 20 terms; every abbreviation in the existing abbreviation check is a term;
on tutorial, topic and how-to pages the first use per `##` section links to it and later uses do
not (FR-016).

## Forward

| Attribute | Rule |
|---|---|
| old address | as published, without suffix |
| target | a page that exists, or the build fails |
| anchor map | optional: old anchor → new address and anchor |

**Behaviour**: a reader at the old address lands at the target, with the anchor carried across —
mapped where the map has it, unchanged otherwise (FR-010, FR-021). The stub is excluded from
search engines and the site's search. Contract: [contracts/forwards.md](./contracts/forwards.md).

**Counts**: 19 forwarded addresses (16 new, 3 existing retargeted), 3 anchor maps. The README's
link to part 1 is updated to the new address rather than forwarded.

## Box

| Kind | Use |
|---|---|
| note | a fact the reader needs next to the text |
| warning | something that will fail or cost data if ignored |
| see also | where to read on — every topic guide ends with one pointing at its reference (FR-020) |
| you will learn | the top of a tutorial part or topic guide (FR-018) |

All four are distinct from each other and from running text, in both colour schemes (FR-017).
