# Vendored, not installed

`axe.min.js` is the accessibility ruleset the site's check injects into each rendered page
(`tests/site/test_a11y.py`, FR-034). It is vendored rather than installed for the same reason the
zoo vendors it: the check must test the same ruleset every time, and a check whose rules change
under it reports a different answer on an unchanged page.

It is **never deployed**. It is not part of the published site, and not part of the distribution —
the wheel ships `src/caravan` and nothing else.

- Licence: MPL-2.0, full text in `MPL-2.0.txt` beside it. Deque Systems, Inc.
- Version: axe-core 4.14.0.
- Copied on 2026-10-27 from the Mobility Model Zoo's vendored copy, which records the upstream
  file's sha256 in the header.

Upgrading it is a deliberate act: a new version can report findings the previous one did not, so it
belongs in a change of its own rather than riding along with a page edit.
