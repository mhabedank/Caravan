# Contract: reference objects

Four kinds, registered in `docs/_ext/caravan_objects.py` (research R1). Declared once, on the
reference page; linked by name from anywhere.

| Kind | Declared in | Directive | Role in running text | Example |
|---|---|---|---|---|
| manifest field | `ref/manifest/<section>` | ```` ```{manifest-field} export.targets ```` | `` {mf}`export.targets` `` | the boards the model must fit |
| CLI command | `ref/cli` | ```` ```{cli} caravan export ```` | `` {cmd}`caravan export` `` | |
| validation rule | `ref/rules` | ```` ```{rule} V-1 ```` | `` {rule}`V-1` `` | |
| board | `ref/boards` | ```` ```{board} esp32 ```` | `` {board}`esp32` `` | |

## An entry

```markdown
```{manifest-field} export.targets
**Type** list of board identifiers · **Default** required

The boards the model has to fit. …
```
```

Every entry states, in this order: the **type** (where the kind has one) and the **default** on its
first line, then what it **does** and **when to change it**. They are content, not directive
options: the built-in object directive takes none, and a custom directive to add two would be code
the site does not need. Today's "Does / Default / Change it / Extremes" content moves
into the entry unchanged, except where the no-hedging rule ([writing.md](./writing.md)) applies.

## Names

- A manifest field is named by its full dotted path as the manifest reference already writes it:
  `export.targets`, `input_features[].type`, `trainer.epochs`.
- A command is `caravan <verb>`, one per verb of the CLI's fixed set.
- A rule is its code as the validator reports it: `V-1`, `CF-4`. A retired rule keeps an entry that
  says it is retired, so an old link and an old error message still resolve.
- A board is the identifier `export.targets` accepts: `esp32`, `stm32h743`, `s32k144`.

## Guarantees

- One entry per object; the existing reference check proves every object the code defines has one.
- An unknown name in a role fails the build (`nitpicky = True` and `-W`, research R2).
- Every object appears in the generated index as "name (kind)".
- Anchors are Sphinx's: `<kind>-<name>`. They are never written by hand; the anchor maps of
  [forwards.md](./forwards.md) read them from the build.
