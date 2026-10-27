# The three promises, and what has not been measured

Not a published page. This is the record SC-001 to SC-004 and SC-009 are settled in, and today it
records that four of them are **not settled**, because they cannot be measured by the person who
built the site.

## What is measured, and by what

| Criterion | What it asks | State |
|---|---|---|
| SC-005 | every leg ends in a result the reader verified | **met** — `tests/contract/test_docs_legs.py` holds every leg to a `leg-check` block, and `tests/train/test_route_legs.py` executes those blocks |
| SC-007 | every abbreviation expanded at first use | **met** — `tests/contract/test_docs_glossary.py` |
| SC-008 | every setting has its four paragraphs | **met** — `tests/contract/test_docs_reference.py`, against the schema, so a new field fails until it is documented |
| SC-010 | the withdrawn board appears nowhere | **met** — `tests/contract/test_docs_hygiene.py`, on the sources and on the built HTML |
| SC-011 | no internal artifacts, provenance intact | **met** — same file, plus `test_docs_hardware.py` |
| SC-012 | AA in both schemes, no sideways scroll | **met** — `tests/site/test_a11y.py`: 24 pages × 2 schemes, 0 violations; no overflow at 390px or at 195px (200% zoom) |
| SC-013 | no address that worked before returns nothing | **met** — `test_docs_hygiene.py` checks the map and the built stubs |
| SC-014 | a deliberate break fails the checks | **met** — tried on 2026-10-27: an unexplained abbreviation fails the glossary check naming the page and the expected expansion; a dead link fails the `-W` build |
| SC-015 | builds and reads offline from a clean checkout | **met** — `sphinx-build -W` with the pinned group; no account, no key, no network beyond fetching the build tools |
| SC-016 | no hardware figure without exactly one label | **met** — `test_docs_hardware.py` |

## What is not measured

**SC-001, SC-002 (the three seconds), SC-003 (fifteen minutes), SC-004 (thirty minutes) and SC-009
(the template choice) are open.** All five are measurements over *people*, and five readers who do
not know the project are the instrument. There is no substitute: the author of a page is the one
person who cannot tell whether it reads in three seconds.

What stands in for them today is weaker and should not be mistaken for them:

- the route has been **executed** end to end by a check, so the instructions work — but "the
  commands run" is not "a reader gets through it in fifteen minutes";
- the firmware **compiles** in continuous integration, so leg 3's path is real — but no board run is
  recorded yet, so thirty minutes to an answering board is an estimate from the leg's own steps;
- the first screen was written against the criteria and its structure is checked
  (`tests/contract/test_docs_landing.py`) — but structure is not comprehension.

## The protocol, for whoever runs it

**Three seconds (SC-001, SC-002).** At least five people who do not know Caravan. Show the first
screen for five seconds on a laptop, then take it away. Ask: what does it produce and from what;
what does it refuse to do; what is the next step. Pass is four of five on the first two questions
and five of five on the third.

**Fifteen minutes (SC-003).** Five developers, clean machines, **the install already done**, timer
started at the first instruction of leg 1. Record the wall-clock time at which an int8 model file
first exists. Pass is four of five inside fifteen minutes. Record also whether the download weight
was stated to them beforehand — the claim is defined with the install excluded, so it depends on
that disclosure being real.

**Thirty minutes (SC-004).** The same runs continued on a generic ESP32, counting only those who had
the board and its toolchain ready. Pass is four of five with the board answering inside thirty
minutes of the same start.

**The template choice (SC-009).** Five readers, three described datasets, asked which template each
calls for. Pass is four of five picking the one the site's guidance implies.

## Results

| Date | Criterion | Sample | Machine | Result |
|---|---|---|---|---|
| — | — | — | — | none yet |

Fill a row per run, with the date, how many people, and what they were working on. A promise
measured once and not written down is a promise the next change can break in silence.
