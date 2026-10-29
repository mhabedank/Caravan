# Contract: the weight gate (FR-029, SC-009)

The one check this feature adds. It exists because Principle V does not allow a budget that nothing
measures, and because the clarification chose a figure for exactly that reason.

## What it measures

The **sum of apparent file sizes of the served build output, excluding `.doctrees`**.

Measured on 2026-10-28, the three plausible methods disagree by up to 190%, so the method is part of
the contract rather than an implementation detail (R1):

| Method | Today's figure | Verdict |
|---|---|---|
| whole output directory | 2,044 KB | wrong: includes `.doctrees`, which is never served |
| `du` excluding `.doctrees` | 840 KB | wrong: 4 KB block rounding over 51 small files |
| **apparent bytes excluding `.doctrees`** | **720,306 B** | the contract |

## The ceiling

**3,000,000 bytes.** Read as decimal, the strict reading of the 3 MB the owner chose. Today's site
uses 24% of it; nineteen placed images at the zoo's observed rate project 2,764,300 B, about 92% of
it (R2).

## Behaviour

- Exceeding the ceiling **fails with a non-zero exit code**. It does not warn (Principle V).
- The figure is printed on every run, pass or fail, with the margin remaining — a budget nobody can
  see the headroom of is one that fails as a surprise.
- The ceiling is **committed in the check**. There is no flag, environment variable or configuration
  switch that raises or silences it (FR-029, Principle V).
- A build the check cannot measure fails. It does not pass on the grounds of uncertainty
  (Principle V: "a stage that cannot determine whether a budget holds MUST fail, not pass").

## Where it runs

One step in the existing `docs-checks` workflow, after the site build that already happens there.
It adds no dependency, no browser and no job; the measurement is a file walk over 51 files and is
immeasurable against the ten minutes the constitution bounds that job to (SC-007).

This is the tension recorded in the plan's Complexity Tracking: FR-010 says the documentation job
must not grow, and this grows it by a file walk. The alternative — asserting the weight in prose —
is the thing Principle V forbids.
