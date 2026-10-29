"""Reading the images an ``image`` column names (feature 010, research R7).

Behind the ``train`` extra: it decodes with the framework the extra already installs — PNG, JPEG,
BMP and the first frame of a GIF — so no installation that reads data lacks it, and no dependency is
added (Principle XII). Nothing here runs on a device: the device receives frames at the declared
size as raw 8-bit pixels, and resizing exists only to train on images of another size.

Everything a pixel goes through is stated: the channel conversion (grey to colour, colour to grey,
an alpha channel dropped) and the resize, Ludwig's two methods — ``interpolate`` (bilinear) and
``crop_or_pad`` — with the result rounded and clipped to 0-255, which is what a camera delivers.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from caravan.manifest.errors import RULE_IMAGE_UNREADABLE, run_rule_error

#: What this build reads, by the bytes a file starts with — a file is what it contains, not what it
#: is called.
SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"BM", "bmp"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
)
FORMATS = ("png", "jpeg", "bmp", "gif")


def image_format(data: bytes) -> str | None:
    return next((name for magic, name in SIGNATURES if data.startswith(magic)), None)


def _decode(path: Path, where: str) -> tuple[np.ndarray, str]:
    """One image as uint8 (height, width, channels), and its format; DS-17 when it cannot be."""
    import tensorflow as tf

    data = path.read_bytes()
    kind = image_format(data)
    if kind is None:
        run_rule_error(
            RULE_IMAGE_UNREADABLE,
            "dataset",
            f"{where}: {path.name} is not an image this build reads",
            found=path.name,
            accepted=FORMATS,
        )
    try:
        image = tf.io.decode_image(data, channels=0, expand_animations=False).numpy()
    except Exception as error:  # the framework's own hierarchy; the text is what matters
        run_rule_error(
            RULE_IMAGE_UNREADABLE,
            "dataset",
            f"{where}: {path.name} could not be decoded as {kind} ({error})",
            found=path.name,
        )
    return image.astype(np.uint8), kind


@dataclass
class ImageReport:
    """What reading did to the images, for the data stage's record."""

    images: int = 0
    resized: int = 0
    converted: int = 0
    formats: dict[str, int] = field(default_factory=dict)

    def count(self, kind: str) -> None:
        self.images += 1
        self.formats[kind] = self.formats.get(kind, 0) + 1


def _where(record: int, column: str) -> str:
    return f"record {record + 1}, column {column}"


def sizes(
    root: Path, paths: Sequence[str], column: str
) -> tuple[list[tuple[int, int, int]], dict[str, int]]:
    """Height, width and channels of every image, in record order, and how many of each format."""
    out = []
    formats: dict[str, int] = {}
    for index, relative in enumerate(paths):
        image, kind = _decode(root / relative, _where(index, column))
        height, width, channels = image.shape
        out.append((int(height), int(width), 3 if channels == 4 else int(channels)))
        formats[kind] = formats.get(kind, 0) + 1
    return out, formats


def _channels(image: np.ndarray, wanted: int) -> tuple[np.ndarray, bool]:
    have = image.shape[-1]
    if have == 4:
        image, have = image[..., :3], 3
    if have == wanted:
        return image, False
    if wanted == 1:
        # ITU-R BT.601 luma, the weights tf.image.rgb_to_grayscale uses.
        grey = image.astype(np.float32) @ np.array([0.2989, 0.587, 0.114], dtype=np.float32)
        return np.clip(np.round(grey), 0, 255).astype(np.uint8)[..., None], True
    return np.repeat(image, 3, axis=-1), True


def _resize(image: np.ndarray, height: int, width: int, method: str) -> np.ndarray:
    import tensorflow as tf

    if method == "crop_or_pad":
        result = tf.image.resize_with_crop_or_pad(image, height, width).numpy()
    else:
        result = tf.image.resize(image.astype(np.float32), (height, width), method="bilinear")
        result = np.clip(np.round(result.numpy()), 0, 255)
    return result.astype(np.uint8)


def load(
    root: Path,
    paths: Sequence[str],
    fitted: dict[str, Any],
    column: str,
    records: Sequence[int] | None = None,
    report: ImageReport | None = None,
) -> np.ndarray:
    """The images at the fitted size and channels, float32 0-255, shape (n, h, w, c).

    Float32 because that is what the Keras model takes; the converted model takes the same values
    as uint8 at scale 1 (research R6), so nothing is lost.
    """
    height, width = int(fitted["height"]), int(fitted["width"])
    channels = int(fitted["num_channels"])
    out = np.zeros((len(paths), height, width, channels), dtype=np.float32)
    for index, relative in enumerate(paths):
        record = index if records is None else int(records[index])
        image, kind = _decode(root / relative, _where(record, column))
        image, converted = _channels(image, channels)
        resized = image.shape[:2] != (height, width)
        if resized:
            image = _resize(image, height, width, fitted["resize_method"])
        out[index] = image
        if report is not None:
            report.count(kind)
            report.resized += int(resized)
            report.converted += int(converted)
    return out


def fit_image(
    root: Path, paths: Sequence[str], stated: dict[str, Any], column: str, path: str
) -> dict[str, Any]:
    """The size an image input is brought to: stated, or taken from the data when it agrees.

    Principle I: what the data says is not asked again — but only when it says one thing. Images of
    several sizes with no size stated are refused (DS-17), naming the sizes found: picking one
    would decide the device's frame for the author.
    """
    from caravan.manifest.resolve import DERIVED

    found, formats = sizes(root, paths, column)
    fitted: dict[str, Any] = {"resize_method": stated["resize_method"]}
    taken: list[str] = []
    for key, axis in (("height", 0), ("width", 1), ("num_channels", 2)):
        if stated[key] != DERIVED:
            fitted[key] = int(stated[key])
            continue
        values: dict[int, int] = {}
        for size in found:
            values[size[axis]] = values.get(size[axis], 0) + 1
        if len(values) != 1:
            described = ", ".join(
                f"{value} in {count} image{'s' if count != 1 else ''}"
                for value, count in sorted(values.items())
            )
            run_rule_error(
                RULE_IMAGE_UNREADABLE,
                f"{path}.preprocessing.{key}",
                f"the images do not all have one {key.replace('num_', '')} ({described}) and "
                f"no {key} is stated",
                found=sorted(values),
                accepted=(f"a stated {key}, to which every image is brought",),
            )
        (value,) = values
        fitted[key] = 3 if key == "num_channels" and value not in (1, 3) else int(value)
        taken.append(key)
    fitted["taken_from_data"] = taken
    fitted["images"] = len(found)
    fitted["resized"] = sum(1 for size in found if size[:2] != (fitted["height"], fitted["width"]))
    fitted["converted"] = sum(1 for size in found if size[2] != fitted["num_channels"])
    fitted["formats"] = dict(sorted(formats.items()))
    return fitted
