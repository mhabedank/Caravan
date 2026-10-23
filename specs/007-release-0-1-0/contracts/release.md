# Contract: the release procedure

## A candidate (`v0.1.0rcN`)

1. On `main`, set the version to `0.1.0rcN` in `pyproject.toml` and `src/caravan/__init__.py`, in
   one commit. CI must be green.
2. After the owner's go-ahead, tag `v0.1.0rcN` and push the tag.
3. The workflow `release.yml` runs:
   - **check**: the tag equals the version; the full suite on 3.13 with both extras; the guide test;
   - **build**: wheel and sdist from the tag; `caravan --version` from a clean 3.13 install with
     both extras and from a clean 3.14 install without extras;
   - **release**: a GitHub pre-release for the tag, with the release note as body and the wheel and
     sdist attached;
   - **verify**: on a fresh runner, the guide's `fetch`, `install` and `run` blocks literally,
     against the published release.
4. If **check** or **build** fails, nothing is published. Fix on `main`, then tag the next
   candidate; a tag is never moved or deleted.
5. If **verify** fails, the release exists and is broken. Its notes get one line saying so and
   naming the next candidate, which follows as in step 4.

## The release (`v0.1.0`)

Allowed only when the port of `pace-cnn` has run with a candidate (spec FR-014) and every Caravan
defect it found is fixed with a test (FR-015). Then:

1. Set the version to `0.1.0`.
2. Complete `docs/releases/0.1.0.md`:
   - the port's result, with its run report's numbers and labels;
   - the gate checklist, with links to the workflow runs.
3. Mark v0.1 released in `docs/roadmap.md`.
4. After the owner's go-ahead, tag `v0.1.0`. The workflow publishes a full release, not a
   pre-release.

## What is never done

- Upload to the package index (owner decision 2026-10-23).
- Move, delete or re-push a tag.
- Publish anything the `pace-cnn` port produced (FR-020).
