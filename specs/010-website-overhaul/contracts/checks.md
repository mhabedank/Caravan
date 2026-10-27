# Contract: what is checked, and where it runs

Every claim this feature makes about the site has a check behind it, and every check has a job it
runs in. The split follows the cost rule the owner set: the framework matrix is for code, and the
site's own checks are for the site.

## In the documentation job, on a change to the site

Runs on `docs/**`, `README.md` and the site's pinned tools. One Python, no extras.

Amended by D5 after the implementation: what the site gets is a short list of cheap checks, not a
test suite. These are the ones that survived, and each is here because it catches the pages drifting
away from the code rather than because it polices prose someone just wrote.

| Check | Asserts | Requirement |
|---|---|---|
| Reference against the code | Every command, option, manifest field, rule and board the code has is named on a page | FR-021 |
| No unexplained abbreviation | Every abbreviation on a page is expanded at its first use on that page | FR-018 |
| Leg 1's strings | Its install and fetch commands name this version | — |
| The release note's shape | Its sections are present and the change note is linked | — |
| Site build, warnings as errors | No broken link, no dead anchor, no page outside a table of contents | FR-046 |
| Every address resolves | Each address published before the overhaul reaches a page or a forward | FR-045 |
| Hygiene | No mention of the withdrawn board; no spec directory, feature number, plan or task file | FR-039, FR-043 |

Together these are about a second, on one Python, with no extras and no browser.

**Deleted by D5**, having served during the overhaul and found real defects there: the browser
accessibility audit and its vendored ruleset, browser and dependency group; the design-token
checks; the landing and leg structure checks; the provenance check; and the rule that forced four
paragraphs per setting. The prose and the design they guarded are unchanged — what is gone is the
machinery that re-checked them forever. FR-029, FR-006 and the provenance rule are held by review
against the written design language and the constitution instead.

## In the firmware job, on a change to what the firmware compiles, and before every release

| Check | Asserts | Requirement |
|---|---|---|
| The generic project builds | The exported C and the firmware compile for a generic ESP32 | FR-042 |
| The deployment leg's blocks, as written | The commands the leg gives a reader run in order and succeed | FR-042 |
| The owner's board still builds | Unchanged, kept out of the site | D2 |
| The linker's figures | Recorded into the run summary, labeled as not measured on a board | Principle IV |

Called by the release workflow before anything is published, as it already is: a firmware that does
not build blocks the release.

## In the framework matrix, unchanged

The page-against-code checks live in the suite, so any change that touches code runs them too, on
every supported Python. Executing the route's commands end to end needs the training framework and
stays where it is — one job, on code changes, and against the published release at release time.

## What is measured by hand, not by a job

The three headline promises are measurements over people, and no job can stand in for them
(SC-001 to SC-004): the five-second exposure test for the first screen, and the timed runs to an
int8 model and to an answering board. The plan's obligation is that the result is recorded with its
date, sample size and the machine, not that it is automated.
