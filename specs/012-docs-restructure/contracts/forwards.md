# Contract: forwards

The site is static files on GitHub Pages, so a forward is a stub page (research R5). It extends the
existing `docs/_ext/redirects.py`; the map stays in `conf.py` as `caravan_redirects`.

## Shape

```python
caravan_redirects = {
    "route/1-first-model": "intro/tutorial01",             # a page that moved whole
    "reference/cli": {                                      # a page whose anchors changed
        "to": "ref/cli",
        "anchors": {"caravan-export": "ref/cli#<anchor read from the build>", …},
    },
}
```

## Behaviour of a stub

1. **A script runs first**: if the address has an anchor and the map has it, go to the mapped
   address; otherwise go to the target with the reader's anchor appended unchanged. It uses
   `location.replace`, so the stub does not stay in the browser's history.
2. **A meta refresh follows** as the fallback for a browser without scripts. It goes to the target
   page, without the anchor.
3. The stub carries `<meta name="robots" content="noindex, follow">` and a canonical link to the
   target, and no content of its own — it never appears in the site's search, which indexes pages,
   not stubs.

## Build-time guarantees

- A forward to a page that does not exist fails the build (already true).
- **New**: an anchor map entry whose target anchor is not in the new build fails the build, naming
  the old anchor. A map that silently sends a reader to the top of the page is the defect this
  contract exists to prevent.
- **New**: a forward that points at another forward fails the build.

## The anchor maps

The old side is recorded from the build of feature 011 (54 anchors on the manifest page, 12 on the
CLI page, 62 on the rules page). The new side is resolved against the new build by object name:
old `#caravan-export` belongs to the command `caravan export`, whose entry is wherever the build put
it. Section anchors that are not objects (`#exit-codes`, `#top-level`) map to the heading that took
their place.
