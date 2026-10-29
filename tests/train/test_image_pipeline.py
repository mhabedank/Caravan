"""Images as an input type, from manifest to export (feature 010, User Story 3)."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

from caravan.cli.main import EXIT_RULE, main
from caravan.manifest.errors import RULE_FLOOR_EXCEEDS_BOARD, RULE_IMAGE_UNREADABLE
from tests.train.conftest import latest_run

REPOSITORY = Path(__file__).resolve().parents[2]
EXAMPLE = REPOSITORY / "examples" / "images-conv2d.yaml"
GENERATOR = REPOSITORY / "tests" / "fixtures" / "datasets" / "images" / "make.py"


def generator():
    spec = importlib.util.spec_from_file_location("images_make", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def png(height: int, width: int, value: int = 120) -> bytes:
    return generator().png([[(value, value // 2, 255 - value)] * width for _ in range(height)])


def run(command: str, manifest: Path, workspace) -> int:
    runs, cache = workspace
    return main([command, str(manifest), "--runs-dir", str(runs), "--cache-dir", str(cache)])


def findings(workspace) -> list[dict]:
    runs, _ = workspace
    return json.loads((latest_run(runs) / "report.json").read_text(encoding="utf-8"))["findings"]


def image_dataset(root: Path, files: dict[str, bytes], labels: list[str] | None = None) -> Path:
    data = root / "data"
    (data / "img").mkdir(parents=True)
    names = sorted(files)
    for name in names:
        (data / name).write_bytes(files[name])
    labels = labels or [("a", "b")[index % 2] for index in range(len(names))]
    rows = ["image,label", *(f"{n},{label}" for n, label in zip(names, labels, strict=True))]
    (data / "labels.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return data


def manifest(
    root: Path, data: Path, preprocessing: str = "{}", blocks: str = "", targets: str = "stm32h743"
) -> Path:
    path = root / "probe.yaml"
    path.write_text(
        f"""apiVersion: caravan/v0.2
model:
  name: probe
  version: 0.0.1
  template: conv2d
  params:
    blocks: [{blocks or "{filters: 4, kernel: 3, padding: same}"}]
input_features:
  - {{name: image, type: image, preprocessing: {preprocessing}}}
output_features:
  - {{name: label, type: category, accuracy_drop_max: 0.5}}
dataset: {data}
trainer: {{epochs: 1}}
export: {{targets: [{targets}], representative_samples: 100}}
""",
        encoding="utf-8",
    )
    return path


# --- the example, end to end ----------------------------------------------------------------


@pytest.fixture(scope="module")
def exported(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("images")
    previous = Path.cwd()
    os.chdir(root)
    try:
        assert run("export", EXAMPLE, (root / "runs", root / "cache")) == 0
    finally:
        os.chdir(previous)
    return latest_run(root / "runs")


def test_the_example_runs_end_to_end_with_the_gate_passing(exported) -> None:
    # SC-012.
    record = json.loads((exported / "quantization.json").read_text(encoding="utf-8"))
    assert record["gate"]["verdict"] == "pass"
    assert record["calibration"]["bounds_frames"] == 2


def test_the_device_passes_raw_pixels(exported) -> None:
    contract = json.loads((exported / "model" / "interface.json").read_text(encoding="utf-8"))
    (entry,) = contract["inputs"]
    assert (entry["type"], entry["dtype"], entry["scale"], entry["zero_point"]) == (
        "image",
        "uint8",
        1.0,
        0,
    )
    assert entry["shape"] == [1, 16, 16, 3]
    assert (entry["height"], entry["width"], entry["num_channels"]) == (16, 16, 3)
    assert entry["channel_order"] == "RGB"
    assert "does not resize" in entry["frame"]
    assert contract["window_size"] is None and contract["stride"] is None
    windows = (exported / "model" / "test_windows.h").read_text(encoding="utf-8")
    assert "static const uint8_t kInput_image" in windows


def test_the_size_was_taken_from_the_data(exported) -> None:
    fitted = json.loads((exported / "data" / "preprocessing.json").read_text(encoding="utf-8"))
    image = fitted["input_features"]["image"]
    assert image["taken_from_data"] == ["height", "width", "num_channels"]
    assert (image["images"], image["resized"], image["converted"]) == (180, 0, 0)
    assert image["formats"] == {"png": 180}


def test_the_fit_check_counts_one_byte_per_pixel(exported) -> None:
    fit = json.loads((exported / "model" / "fit.json").read_text(encoding="utf-8"))
    ram = next(floor for floor in fit["floors"] if floor["resource"] == "ram")
    assert "1 for an image's pixels" in ram["method"]


# --- reading images ----------------------------------------------------------------------------


def test_jpeg_files_are_read(tmp_path, workspace) -> None:
    import tensorflow as tf

    files = {}
    for index in range(40):
        pixels = tf.fill((16, 16, 3), tf.constant(40 + 4 * index, dtype=tf.uint8))
        files[f"img/{index:02d}.jpg"] = tf.io.encode_jpeg(pixels).numpy()
    data = image_dataset(tmp_path, files)
    assert run("build", manifest(tmp_path, data), workspace) == 0
    runs, _ = workspace
    fitted = json.loads((latest_run(runs) / "data" / "preprocessing.json").read_text())
    assert fitted["input_features"]["image"]["images"] == 40
    assert fitted["input_features"]["image"]["formats"] == {"jpeg": 40}


def test_images_of_several_sizes_need_a_stated_size(tmp_path, workspace) -> None:
    files = {f"img/{i:02d}.png": png(16, 16) for i in range(20)}
    files["img/99.png"] = png(24, 20)
    data = image_dataset(tmp_path, files)
    assert run("build", manifest(tmp_path, data), workspace) == EXIT_RULE
    finding = next(f for f in findings(workspace) if f.get("rule") == RULE_IMAGE_UNREADABLE)
    assert finding["path"] == "input_features[0].preprocessing.height"
    assert "16 in 20 images" in finding["problem"] and "24 in 1 image" in finding["problem"]


def test_a_stated_size_brings_every_image_to_it(tmp_path, workspace) -> None:
    files = {f"img/{i:02d}.png": png(16, 16) for i in range(20)}
    files["img/99.png"] = png(24, 20)
    data = image_dataset(tmp_path, files)
    preprocessing = "{height: 16, width: 16, num_channels: 1}"
    assert run("build", manifest(tmp_path, data, preprocessing), workspace) == 0
    runs, _ = workspace
    image = json.loads((latest_run(runs) / "data" / "preprocessing.json").read_text())[
        "input_features"
    ]["image"]
    assert (image["resized"], image["converted"], image["num_channels"]) == (1, 21, 1)
    built = json.loads((latest_run(runs) / "model" / "built.json").read_text())
    assert built["inputs"][0]["shape"] == [16, 16, 1]


def test_a_file_that_is_not_an_image_is_refused_with_its_record(tmp_path, workspace) -> None:
    files = {f"img/{i:02d}.png": png(16, 16) for i in range(20)}
    files["img/07.png"] = b"not an image at all"
    data = image_dataset(tmp_path, files)
    assert run("build", manifest(tmp_path, data), workspace) == EXIT_RULE
    finding = next(f for f in findings(workspace) if f.get("rule") == RULE_IMAGE_UNREADABLE)
    assert "record 8, column image" in finding["problem"]
    assert "07.png is not an image this build reads" in finding["problem"]


# --- the reference shape and the fit check ------------------------------------------------------


MOBILENET_POINTWISE = [16, 32, 32, 64, 64, 128, 128, 128, 128, 128, 128, 256, 256]
MOBILENET_STRIDE_TWO = {2, 4, 6, 12}


def test_mobilenet_at_width_a_quarter_has_the_reference_count_plus_its_biases() -> None:
    # SC-013. Keras's MobileNetV1 drops the convolution bias; this template keeps it (research
    # R4), so the two counts differ by exactly one bias per convolution output channel.
    import keras

    from caravan.templates.builders import load_builder

    blocks = [{"filters": 8, "kernel": 3, "stride": 2, "padding": "same", "normalise": True}] + [
        {
            "kind": "separable",
            "filters": filters,
            "kernel": 3,
            "stride": 2 if position in MOBILENET_STRIDE_TWO else 1,
            "padding": "same",
            "normalise": True,
        }
        for position, filters in enumerate(MOBILENET_POINTWISE, start=1)
    ]
    model = load_builder("conv2d")({"blocks": blocks}, (96, 96, 3), ["no", "yes"])
    reference = keras.applications.MobileNet(
        input_shape=(96, 96, 3), alpha=0.25, weights=None, classes=2
    )
    channels_in = [8, *MOBILENET_POINTWISE[:-1]]
    biases = 8 + sum(
        depthwise + pointwise
        for depthwise, pointwise in zip(channels_in, MOBILENET_POINTWISE, strict=True)
    )
    assert reference.count_params() == 219_058
    assert model.count_params() == reference.count_params() + biases == 221_794


def test_an_image_counted_as_bytes_fits_where_floats_would_not(tmp_path, workspace) -> None:
    # 128 x 128 x 3 is 49,152 bytes as pixels and 196,608 as float32: the s32k144's 64 KiB holds
    # the first and not the second, so a floor counting floats would refuse a model that fits.
    files = {f"img/{i:02d}.png": png(128, 128, 10 * i) for i in range(20)}
    data = image_dataset(tmp_path, files)
    path = manifest(
        tmp_path,
        data,
        blocks="{filters: 2, kernel: 3, stride: 4, padding: same}",
        targets="s32k144",
    )
    assert run("build", path, workspace) == 0


def test_an_image_whose_floor_exceeds_the_board_stops_before_training(tmp_path, workspace) -> None:
    # 160 x 160 x 3 = 76,800 bytes of pixels, plus the first convolution's 40 x 40 x 2 output:
    # a floor of 80,000 bytes against 65,536 bytes of RAM (rule F-1).
    files = {f"img/{i:02d}.png": png(160, 160, 10 * i) for i in range(20)}
    data = image_dataset(tmp_path, files)
    path = manifest(
        tmp_path,
        data,
        blocks="{filters: 2, kernel: 3, stride: 4, padding: same}",
        targets="s32k144",
    )
    assert run("train", path, workspace) == EXIT_RULE
    finding = next(f for f in findings(workspace) if f.get("rule") == RULE_FLOOR_EXCEEDS_BOARD)
    assert "s32k144 ram: the floor is 80,000 bytes" in json.dumps(finding["found"])
    runs, _ = workspace
    assert not (latest_run(runs) / "model" / "trained.keras").exists()
