# Contract: every address, and where it goes

The site publishes thirteen pages today. This is what each becomes, and what forwards from it. It
is the contract FR-045 is checked against: no address that worked before may end nowhere after.

## Addresses that move

| Today | After | Forward |
|---|---|---|
| `index.html` | The landing page, rewritten (FR-001 to FR-006) | same address |
| `try-it.html` | Split into `route/1-first-model` and `route/2-your-columns` | → `route/` |
| `guides/own-project.html` | Folded into `route/2-your-columns`, with the deeper material in `concepts/feature-types` | → `route/2-your-columns` |
| `guides/lora32.html` | Removed. Its hardware story is rewritten for a generic ESP32 in `route/3-onto-a-board` | → `route/3-onto-a-board`, `noindex` |
| `board-runs/index.html` | Kept, with the withdrawn board's name out of it and its claim restated as not yet verified (FR-040) | same address |
| `reference/cli.html` | Kept, entries gain their prose (FR-020, FR-021) | same address |
| `reference/manifest.html` | Kept as lookup; every setting's explanation moves into it or into a concept page (FR-020, FR-024) | same address |
| `reference/rules.html` | Kept, each rule stated in words rather than as a code (FR-022) | same address |
| `compatibility.html` | Kept, the withdrawn board's rows re-grounded or marked unverified (FR-040) | same address |
| `budgets.html` | Kept; its concepts move to `concepts/budgets-and-gates` and it keeps the measurements | same address |
| `manifest-changes.html` | Kept, internal artifact citations replaced by what the site itself can show (FR-043, FR-044) | same address |
| `roadmap.html` | Kept, feature numbers out (FR-043) | same address |
| `releases/0.1.0.html` | Kept, feature numbers and the withdrawn board out (FR-039, FR-043) | same address |

## Addresses that are new

`route/`, `route/1-first-model`, `route/2-your-columns`, `route/3-onto-a-board`,
`route/4-when-it-does-not-fit`, `concepts/templates`, `concepts/feature-types`,
`concepts/budgets-and-gates`, `concepts/what-a-run-leaves`.

## What a forward is

A stub page carrying a meta refresh to its target and a canonical link to it, marked `noindex`, in
no navigation, with no content of its own. Generated from a map in the site's configuration (R6),
so adding a forward is one line rather than a hand-written file.

## What is checked

- Every address in the left column resolves: to a page, or to a forward that resolves.
- Every forward is `noindex` and appears in no table of contents.
- No page in the right column is unreachable from a table of contents, which the existing
  warnings-as-errors build already enforces (FR-046).
