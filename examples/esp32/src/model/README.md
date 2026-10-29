# The export's files go here

Four files, copied out of a run directory by part 3 of the tutorial:

- `model_data.h` — the model as a C array, with a named position for every input and the output
- `model_data.cc` — the array itself
- `resolver.h` — exactly the operators this model needs
- `test_windows.h` — windows of the test part with the answers your computer gave for them

Nothing else belongs here, and nothing in this directory is committed: `.gitignore` keeps everything
but this README out, because the files are yours and are rewritten by every export.

The firmware is model-agnostic. Everything it knows about the model comes from these four files, so
running a different model means copying a different run's files and rebuilding — `src/main.cc` does
not change.
