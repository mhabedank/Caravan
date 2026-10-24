"""UCI HAR, as the zoo's `pace-cnn` 0.1.0 used it, in the form Caravan reads (features 007, 008).

    python ports/pace-cnn/convert.py <har.zip> <output directory outside this repository>

The zoo's benchmark `uci-har-v1` fixes the data, the split and the normalisation, and records a
hash for each. This script reproduces each and checks it against those hashes, so the port is
compared on the same data and the same split:

1. the archive's SHA-256;
2. the nine inertial channels of the pre-cut windows (128 samples at 50 Hz, 50 % overlap), in the
   zoo's order, and the activity of each window;
3. the validation subjects: 3 of the 21 training subjects, drawn as the zoo's `split_subjects`
   draws them; the subject lists and the windows of each part against the benchmark's hashes;
4. the per-channel mean and standard deviation of the training part, against the benchmark's.

It writes one CSV row per time step, 128 rows per window, with `activity`, `split` (`train`,
`validation` or `test`, Ludwig's words) and the nine channels as **raw values**, and a `stats.json`
beside it. Since feature 008 each `number` feature is standardised inside the model, with the mean
and deviation fitted on the training part — the same numbers step 4 checks — so the converter no
longer standardises.

Nothing here trains, labels or evaluates anything (constitution, Principle XI). The data stays
where the author puts it: the output directory must be outside this repository, and nothing it
writes is published (owner decision, 2026-10-23).
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np

#: From the zoo's topics/condition-monitoring/benchmarks/uci-har-v1/manifest.json.
ARCHIVE_SHA256 = "c00b803081a5c797cd5e4b83700a9810b38d53d9d84e01917e090e1fdbc81031"
SPLITS = {
    "train": {
        "windows": 6288,
        "subjects_sha256": "a12bd59fd7c8ff87cb7875191369dbd868545edfbd2ea47b34b616ee615fddac",
        "data_sha256": "288364fa7d33ace725c96a57f4ce7354c2bea6741ab72bd9ec7e4461132185c9",
    },
    "val": {
        "windows": 1064,
        "subjects_sha256": "98e9f8979de3ed820093e2816c12499d770c8b5e8614a619880824d93eb4452c",
        "data_sha256": "625d11ad88477edde9a5873b4d416663e0b12dd37feea9cb162d7027690ec1dc",
    },
    "test": {
        "windows": 2947,
        "subjects_sha256": "dc39201e9809743838633e34b645ba7dcd74b7d2c8cfa367bd8a4f35fc2ca551",
        "data_sha256": "9cf806e4dbf51fee31af6f22030b2d90ca0c76faf5186d724f4f0247bb60d605",
    },
}
#: The normalisation the zoo froze; the standard deviation already carries its +1e-6.
MEAN = [
    -0.0004951871815137565, -0.00032817694591358304, -0.00021286075934767723,
    0.0005902921548113227, -0.0004714796377811581, -0.00026790332049131393,
    0.8028175234794617, 0.02752470225095749, 0.081498883664608,
]  # fmt: skip
STD = [
    0.19266846776008606, 0.1205918937921524, 0.10867609083652496,
    0.4066708981990814, 0.3769063949584961, 0.25676658749580383,
    0.410501092672348, 0.382828027009964, 0.373470276594162,
]  # fmt: skip
VALIDATION_SEED = 2026
VALIDATION_DIVISOR = 7

CHANNELS = [
    "body_acc_x", "body_acc_y", "body_acc_z",
    "body_gyro_x", "body_gyro_y", "body_gyro_z",
    "total_acc_x", "total_acc_y", "total_acc_z",
]  # fmt: skip
LABELS = ["walking", "walking_upstairs", "walking_downstairs", "sitting", "standing", "laying"]
ROOT = "UCI HAR Dataset"
#: The words of a fixed split, per part (feature 008, research R8).
PART_WORDS = {"train": "train", "val": "validation", "test": "test"}


def find_repository(start: Path) -> Path | None:
    """The Caravan checkout this script sits in, or ``None`` for a copy outside one.

    Found by a ``pyproject.toml`` that names the ``caravan-ml`` distribution in a directory above
    the script, never by counting parents: a copy of the script elsewhere would otherwise take a
    stranger's directory for the repository (the defect found on 2026-10-24).
    """
    for directory in start.resolve().parents:
        project = directory / "pyproject.toml"
        if project.is_file() and 'name = "caravan-ml"' in project.read_text(encoding="utf-8"):
            return directory
    return None


REPOSITORY = find_repository(Path(__file__))


def fail(message: str) -> None:
    print(f"convert: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def subjects_sha256(subjects) -> str:
    """As the zoo computes it: the sorted distinct numbers joined by commas."""
    return sha256(",".join(str(s) for s in sorted({int(s) for s in subjects})).encode())


def data_sha256(x: np.ndarray, y: np.ndarray) -> str:
    """As the zoo computes it: the float32 windows in C order, then the int64 labels."""
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(x, dtype=np.float32).tobytes())
    digest.update(np.ascontiguousarray(y, dtype=np.int64).tobytes())
    return digest.hexdigest()


def inner_archive(path: Path) -> zipfile.ZipFile:
    blob = path.read_bytes()
    if sha256(blob) != ARCHIVE_SHA256:
        fail(f"{path} is not the archive the zoo's benchmark names (sha256 {ARCHIVE_SHA256})")
    outer = zipfile.ZipFile(io.BytesIO(blob))
    (name,) = [n for n in outer.namelist() if n.endswith(".zip")]
    return zipfile.ZipFile(io.BytesIO(outer.read(name)))


def read_part(archive: zipfile.ZipFile, part: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Windows (n, 128, 9) in float32, labels 0-5, subjects, for the official train or test."""

    def text(name: str) -> str:
        return archive.read(f"{ROOT}/{part}/{name}").decode()

    channels = [
        np.loadtxt(io.StringIO(text(f"Inertial Signals/{c}_{part}.txt")), dtype=np.float32)
        for c in CHANNELS
    ]
    x = np.stack(channels, axis=-1)
    y = np.loadtxt(io.StringIO(text(f"y_{part}.txt")), dtype=np.int64) - 1
    subjects = np.loadtxt(io.StringIO(text(f"subject_{part}.txt")), dtype=np.int64)
    return x, y, subjects


def validation_subjects(train_subjects: np.ndarray) -> list[int]:
    """The zoo's `split_subjects`: one seventh of the distinct training subjects, drawn once."""
    subs = sorted({int(s) for s in train_subjects})
    drawn = np.random.default_rng(VALIDATION_SEED).choice(
        subs, size=len(subs) // VALIDATION_DIVISOR, replace=False
    )
    return sorted(int(s) for s in drawn)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__.splitlines()[2].strip(), file=sys.stderr)
        return 2
    archive_path, out = Path(argv[0]), Path(argv[1]).resolve()
    if REPOSITORY is not None and (out == REPOSITORY or REPOSITORY in out.parents):
        fail(f"{out} is inside the repository; the data must stay outside it")

    archive = inner_archive(archive_path)
    x_train, y_train, s_train = read_part(archive, "train")
    x_test, y_test, s_test = read_part(archive, "test")

    val = validation_subjects(s_train)
    is_val = np.isin(s_train, val)
    parts = {
        "train": (x_train[~is_val], y_train[~is_val], s_train[~is_val]),
        "val": (x_train[is_val], y_train[is_val], s_train[is_val]),
        "test": (x_test, y_test, s_test),
    }
    for name, (x, y, subjects) in parts.items():
        want = SPLITS[name]
        if len(x) != want["windows"]:
            fail(f"{name}: {len(x)} windows, the benchmark has {want['windows']}")
        if subjects_sha256(subjects) != want["subjects_sha256"]:
            fail(f"{name}: the subjects differ from the benchmark's")
        if data_sha256(x, y) != want["data_sha256"]:
            fail(f"{name}: the windows differ from the benchmark's")

    flat = parts["train"][0].reshape(-1, len(CHANNELS))
    mean, std = flat.mean(0), flat.std(0) + np.float32(1e-6)
    if not (np.allclose(mean, MEAN, atol=1e-6) and np.allclose(std, STD, rtol=1e-5)):
        fail("the training part's mean and standard deviation differ from the benchmark's")

    out.mkdir(parents=True, exist_ok=True)
    with (out / "records.csv").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(",".join(["activity", "split", *CHANNELS]) + "\n")
        for name, (x, y, _) in parts.items():
            for window, label in zip(x, y, strict=True):
                prefix = f"{LABELS[label]},{PART_WORDS[name]},"
                for step in window:
                    handle.write(prefix + ",".join(f"{v:.9g}" for v in step) + "\n")
    stats = {
        "source": "UCI HAR, archive sha256 " + ARCHIVE_SHA256,
        "benchmark": "uci-har-v1 (mobility-model-zoo)",
        "validation_subjects": val,
        "windows": {name: len(x) for name, (x, _, _) in parts.items()},
        "normalisation": {
            "mean": MEAN,
            "std": STD,
            "applied_by": "the model: zscore fitted on the training part (feature 008)",
        },
        "labels": LABELS,
        "channels": CHANNELS,
    }
    (out / "stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    total = sum(len(x) for x, _, _ in parts.values())
    print(f"{out / 'records.csv'}: {total} windows of 128 records, split {stats['windows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
