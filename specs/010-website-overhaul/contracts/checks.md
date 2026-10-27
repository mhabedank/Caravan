# Contract: what is checked, and where it runs

Every claim this feature makes about the site has a check behind it, and every check has a job it
runs in. The split follows the cost rule the owner set: the framework matrix is for code, and the
site's own checks are for the site.

## In the documentation job, on a change to the site

Runs on `docs/**`, `README.md` and the site's pinned tools. One Python, no extras.

| Check | Asserts | Requirement |
|---|---|---|
| Reference against the code | Every command, option, manifest field, rule and board the code has is named on a page | FR-021 |
| Every setting has its prose | Each setting the schema admits carries all four prose fields, not facts alone | FR-020 |
| No unexplained abbreviation | Every abbreviation on a page is expanded at its first use on that page | FR-018 |
| The legs' strings | The install and fetch commands in the route name this version | — |
| The release note's shape | Its sections are present and the change note is linked | — |
| Site build, warnings as errors | No broken link, no dead anchor, no page outside a table of contents | FR-046 |
| Every address resolves | Each address published before the overhaul reaches a page or a forward | FR-045 |
| Hygiene | No mention of the withdrawn board; no spec directory, feature number, plan or task file | FR-039, FR-043 |
| Provenance | No figure about a board without exactly one label | FR-006, SC-016 |
| Tokens | No interface colour outside the token set; the accent only where it is reserved | FR-028, FR-029 |
| Browser audit | No violation at the A or AA level, on every page, in both colour schemes | FR-034, SC-012 |

The audit is the one addition with a real cost: a browser in continuous integration, taking the job
from about a minute and a half to an estimated three to four. It is cached, and the job runs only
when the site changes.

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
