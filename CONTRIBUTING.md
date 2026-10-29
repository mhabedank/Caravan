# Contributing to Caravan

The project's rules live in `.specify/memory/constitution.md`. It takes precedence over this file
and over habit. Two of its rules shape day-to-day work more than the rest, so they are spelled out
here.

## The scope is narrow on purpose

Caravan builds models that run on microcontrollers and comparable constrained hardware. Cloud,
desktop and LLM models are out of scope; so is becoming an inference runtime, a platform
description language, a cycle-accurate simulator or a research-grade architecture search.

A feature that serves only an out-of-scope model is rejected, however small. A feature with no
named model behind it is rejected too: growth follows real need, one model at a time.

## The dependency gate

Before proposing a dependency, answer all five in the pull request. If any answer is missing, the
gate has not been passed.

1. **What does it replace?** Name the code it removes or the capability it adds.
2. **Why can it not be owned here?** Code the project could own in a few hundred readable lines
   must not become a dependency. A YAML parser is a fair dependency; an argument parser is not,
   which is why the command line is built on `argparse`.
3. **Which extra does it belong to?** The default installation carries at most six direct runtime
   dependencies, and the project at most four extras. Anything a user does not need in order to
   check a manifest belongs behind an extra.
4. **Does the budget still hold?** See `docs/ref/budgets.md` for the current measurements. The
   headroom is reserved, not spare.
5. **Does it constrain the Python policy?** The project supports the current and the previous
   stable Python minor version. A dependency that cannot be installed on the current minor —
   because it ships no wheel for it, for instance — does not set the project's policy; it is
   replaced, vendored in the small, or moved behind an extra. This is not hypothetical: it is why
   the YAML dependency is `ruamel.yaml` and not `pyyaml`.

No dependency carries an upper version bound unless a concrete incompatibility is documented with
a reference, and the bound is removed when it is fixed upstream.

## Working on a feature

The repository follows a spec-driven flow; artefacts live under `specs/<nnn>-<name>/`.

```bash
uv sync
uv run pytest                      # the whole suite
uv run pytest tests/layering -q    # the Principle XII checks on their own
uv run ruff check src tests
uv run ruff format src tests
```

Every spec and plan lists the principles it touches and states how it complies. If a change needs
a principle to bend, that is a constitution amendment with its own rationale and version bump —
not a note in a pull request.

## Messages

Every rejection a user sees names the offending field, what was wrong with it and what is accepted
there. A message that contains a library type name, a module path or a traceback is a bug: those
belong to exit code 3 alone. Fixtures under `tests/fixtures/manifests/invalid/` pin one case per
rule, and a test fails if a rule has none.
