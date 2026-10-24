# Port: pace-cnn through Caravan

An internal test of Caravan on a real model before 0.1.0 (feature 007, User Story 4): the zoo's
published `pace-cnn` 0.1.0 is rebuilt through a Caravan release candidate on its own data, with its
own split by subject. Nothing this port produces is published, and the zoo is not changed by it
(owner decision, 2026-10-23).

## Steps

1. Get the UCI HAR archive the zoo's benchmark names: UCI dataset 240,
   <https://archive.ics.uci.edu/dataset/240/human+activity+recognition+using+smartphones>, about
   60 MB. `convert.py` checks its SHA-256.
2. Install the candidate in a fresh Python 3.13 environment, as in `docs/try-it.md`.
3. Convert, into a directory outside this repository:

   ```bash
   python ports/pace-cnn/convert.py har.zip /some/where/uci-har
   ```

   It checks the windows, the subjects and the data of each part, and the training part's mean
   and standard deviation, against the zoo's benchmark `uci-har-v1`. It writes `records.csv`:
   10,299 windows of 128 records, `train` 6,288, `validation` 1,064 and `test` 2,947, as raw
   values. The script can be copied anywhere: it finds this repository, if it sits in one, by its
   `pyproject.toml`, and refuses to write into it.
4. Copy `pace-cnn.yaml`, set `dataset` to that directory, and run `caravan export pace-cnn.yaml`.
   Each of the nine channels is a `number` feature, standardised inside the model with the mean
   and deviation of the training part (feature 008).

## What differs from the zoo's recipe

The task, the data, the split and the normalisation are the zoo's. The recipe is not quite,
because Caravan 0.1.0 cannot express all of it (`specs/007-release-0-1-0/research.md`, R8):

| Zoo | This port | Why |
|---|---|---|
| dropout 0.3 after the pooling head | dropout 0.3 on the last convolution block | the template places dropout per block |
| Adam, cosine decay from 2e-3 | Adam, constant 2e-3 | no learning-rate schedule in 0.1.0 |
| convolutions without bias | with bias | absorbed by batch normalisation; no effect after folding |
| calibration on the first 500 training windows | 500 training windows drawn by seed | Caravan draws its calibration sample |
| macro-F1 and per-subject criteria | accuracy, and the int8 gate of 0.03 | Caravan measures accuracy; 0.03 is the zoo's kill criterion K2 |

So the port reproduces the task, not the exact model. Its numbers are compared with the published
ones and are not expected to equal them.

## The licence, an open item for the zoo

The zoo registers UCI HAR as CC-BY-4.0 for commercial use (its spec 021, FR-027). The README inside
the archive says: "Any commercial use is prohibited." The two statements contradict each other.
Caravan neither checks nor decides data rights (constitution, Principle VI); the owner decided that
this port runs as an internal test only. Resolving the contradiction is the zoo's.

## Result

With typed features (feature 008, `specs/008-typed-features/research.md`, R16): int8 0.917 on the
2,947 test windows with the manifest's `random_seed: 0`, and 0.927 to 0.933 with seeds 1 to 3; the
zoo published 0.923. The final figure is recorded in `docs/releases/0.1.0.md` when 0.1.0 is cut.
