"""The documentation site: Sphinx with MyST, built from docs/ (feature 009, research R1).

Build it with ``uv run --group docs sphinx-build -W -b html docs _site``. ``-W`` turns every warning
into a failed build, which is what makes the checks real: a broken link or anchor, and a page that
is in no table of contents, both stop it.

The version shown on every page comes from ``CARAVAN_VERSION`` when the release workflow builds the
site for a tag, and otherwise from the package's own version, read as text so that building the
documentation never imports Caravan.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def _package_version() -> str:
    source = Path(__file__).resolve().parent.parent / "src" / "caravan" / "__init__.py"
    match = re.search(r'^__version__ = "([^"]+)"', source.read_text(encoding="utf-8"), re.M)
    return match.group(1) if match else "unknown"


project = "Caravan"
author = "Caravan contributors"
copyright = "Apache-2.0"
release = version = os.environ.get("CARAVAN_VERSION") or _package_version()

extensions = ["myst_parser", "redirects", "identity", "caravan_objects"]
# The site's own extension lives beside this file rather than in the package: it builds the site and
# is never installed with Caravan (FR-048).
sys.path.insert(0, str(Path(__file__).resolve().parent / "_ext"))
source_suffix = {".md": "markdown"}
root_doc = "index"
# Working records stay in the repository and are linked as files on GitHub; they are not pages.
exclude_patterns = ["_build", "design/**", "research/**"]

myst_heading_anchors = 3

# A link to a name that has no entry — a field, a command, a rule, a board, a glossary term — is a
# warning with this on, and `-W` makes it a failed build that names the page and the name.
nitpicky = True

# The landing page's h1 is shown in the theme, inside the hero's dark panel, because the panel is
# structure rather than content. It is still WRITTEN in `index.md`, as that page's `# ` title, and
# `_ext/identity.py` drops the title node before the writer turns it into a heading.
#
# The roundabout route is there to keep a check. With no title in the source, every `##` on the
# page is a top-level section and Sphinx renders each as an `<h1>`: seven first-level headings on
# one page. Silencing MyST's complaint about the missing h1 — the first thing tried here — also
# silenced the heading-order check that had caught the manifest reference skipping H2 to H4
# forty-three times. With the title where it belongs, nothing is suppressed and that check is back.
# colon_fence lets a layout wrapper use `:::` so that code blocks inside it keep ```, which is how
# a leg frames the card at its head and the check at its foot.
# attrs_block puts a class on the SECTION a heading opens — `{.band .band-3}` on the line above a
# `##` — which is what gives the landing page its grids.
#
# attrs_block rather than a container directive, and the reason is worth keeping: a heading inside
# a `container` becomes `<p class="rubric">`, not a heading, because docutils does not treat it as
# a document section. The landing page's first draft was built that way and looked right while
# having no structure under it at all. Found by reading the rendered HTML; the accessibility audit
# did not catch it, because its heading rules check the order of the headings that exist.
myst_enable_extensions = ["substitution", "colon_fence", "attrs_block"]
myst_substitutions = {"release": release}

# The identity, copied from the Mobility Model Zoo and carried as a theme of our own (feature 010,
# D1 and research R1). A theme here installs nothing, which Principle XII prefers to a third-party
# theme whose own design decisions would then have to be overridden.
html_theme_path = ["_themes"]
html_theme = "caravan"
# Feature 011: the placed images live in `docs/_static/images/<id>/` — three WebP derivatives and
# the `image.yaml` that records how the image was made. Sphinx copies the tree verbatim, so the
# site build invokes none of the imagery machinery (FR-010) and each record is published beside the
# image it describes, which is what makes the provenance checkable rather than merely filed.
html_static_path = ["_static"]
html_short_title = "Caravan"
html_title = f"Caravan {release}"
html_show_sourcelink = False
html_copy_source = False
html_favicon = None  # the theme links its own, which turns over with the colour scheme

# The header carries two things, as Django's documentation does: "Documentation", which is the
# contents page, and the search the layout adds itself. Everything else is reached through the
# contents page, which is the map a header of a dozen links would be a worse copy of.
# A browser keeps a stylesheet it has seen, so a changed one can sit behind an old page for days:
# the route page's picture showed squashed because of exactly that. Every stylesheet link carries
# this digest of the theme's CSS, so a change to it is a new URL and is fetched.
_THEME_STATIC = Path(__file__).parent / "_themes" / "caravan" / "static"
_STATIC_V = __import__("hashlib").sha256(
    b"".join(f.read_bytes() for f in sorted(_THEME_STATIC.glob("*.css")))
).hexdigest()[:10]

html_context = {
    "static_v": _STATIC_V,
    "nav_pages": [
        ("contents", "Documentation"),
    ],
}

# Addresses that moved. A value is the docname a forward leads to, or, for a page whose anchors
# changed too, {"to": docname, "anchors": {old anchor: "docname#new anchor"}}. Every other forward
# carries the reader's anchor across unchanged. The extension refuses a forward to a page that does
# not exist, a forward to another forward, and a mapped anchor the build does not contain.
caravan_redirects: dict[str, str | dict] = {
    # The tutorial, in four parts, was "the route" in four legs.
    "route/index": "intro/tutorial",
    "route/1-first-model": "intro/tutorial01",
    "route/2-your-columns": "intro/tutorial02",
    "route/3-onto-a-board": "intro/tutorial03",
    "route/4-when-it-does-not-fit": "intro/tutorial04",
    # The concept pages are topic guides.
    "concepts/templates": "topics/templates",
    "concepts/feature-types": "topics/feature-types",
    "concepts/budgets-and-gates": "topics/budgets-and-gates",
    "concepts/what-a-run-leaves": "topics/what-a-run-leaves",
    # The reference guides, under ref/.
    "reference/manifest": {
        "to": "ref/manifest/index",
        "anchors": {
            "manifest-reference": "ref/manifest/index",
            "a-first-manifest": "ref/manifest/index#a-first-manifest",
            "top-level": "ref/manifest/top-level",
            "apiversion": "ref/manifest/top-level#manifest-field-apiVersion",
            "dataset": "ref/manifest/top-level#manifest-field-dataset",
            "random-seed": "ref/manifest/top-level#manifest-field-random_seed",
            "model": "ref/manifest/model",
            "model-name": "ref/manifest/model#manifest-field-model.name",
            "model-version": "ref/manifest/model#manifest-field-model.version",
            "model-template": "ref/manifest/model#manifest-field-model.template",
            "model-params": "ref/manifest/model#manifest-field-model.params",
            "input-features": "ref/manifest/input-features",
            "input-features-name": "ref/manifest/input-features#manifest-field-input_features-.name",
            "input-features-type": "ref/manifest/input-features#manifest-field-input_features-.type",
            "input-features-preprocessing-normalization": "ref/manifest/input-features#manifest-field-input_features-.preprocessing.normalization",
            "input-features-preprocessing-missing-value-strategy": "ref/manifest/input-features#manifest-field-input_features-.preprocessing.missing_value_strategy",
            "input-features-preprocessing-fill-value": "ref/manifest/input-features#manifest-field-input_features-.preprocessing.fill_value",
            "input-features-preprocessing-most-common": "ref/manifest/input-features#manifest-field-input_features-.preprocessing.most_common",
            "input-features-preprocessing-vocab": "ref/manifest/input-features#manifest-field-input_features-.preprocessing.vocab",
            "input-features-preprocessing-fallback-true-label": "ref/manifest/input-features#manifest-field-input_features-.preprocessing.fallback_true_label",
            "input-features-encoder-type": "ref/manifest/input-features#manifest-field-input_features-.encoder.type",
            "input-features-encoder-embedding-size": "ref/manifest/input-features#manifest-field-input_features-.encoder.embedding_size",
            "output-features": "ref/manifest/output-features",
            "output-features-name": "ref/manifest/output-features#manifest-field-output_features-.name",
            "output-features-type": "ref/manifest/output-features#manifest-field-output_features-.type",
            "output-features-preprocessing-vocab": "ref/manifest/output-features#manifest-field-output_features-.preprocessing.vocab",
            "output-features-preprocessing-fallback-true-label": "ref/manifest/output-features#manifest-field-output_features-.preprocessing.fallback_true_label",
            "output-features-preprocessing-normalization": "ref/manifest/output-features#manifest-field-output_features-.preprocessing.normalization",
            "output-features-loss-type": "ref/manifest/output-features#manifest-field-output_features-.loss.type",
            "output-features-loss-class-weights": "ref/manifest/output-features#manifest-field-output_features-.loss.class_weights",
            "output-features-loss-positive-class-weight": "ref/manifest/output-features#manifest-field-output_features-.loss.positive_class_weight",
            "output-features-threshold": "ref/manifest/output-features#manifest-field-output_features-.threshold",
            "output-features-clip": "ref/manifest/output-features#manifest-field-output_features-.clip",
            "output-features-accuracy-drop-max": "ref/manifest/output-features#manifest-field-output_features-.accuracy_drop_max",
            "output-features-mae-increase-max": "ref/manifest/output-features#manifest-field-output_features-.mae_increase_max",
            "preprocessing": "ref/manifest/preprocessing",
            "preprocessing-window-size": "ref/manifest/preprocessing#manifest-field-preprocessing.window_size",
            "preprocessing-split-type": "ref/manifest/preprocessing#manifest-field-preprocessing.split.type",
            "preprocessing-split-probabilities": "ref/manifest/preprocessing#manifest-field-preprocessing.split.probabilities",
            "preprocessing-split-column": "ref/manifest/preprocessing#manifest-field-preprocessing.split.column",
            "defaults": "ref/manifest/defaults",
            "trainer": "ref/manifest/trainer",
            "trainer-epochs": "ref/manifest/trainer#manifest-field-trainer.epochs",
            "trainer-batch-size": "ref/manifest/trainer#manifest-field-trainer.batch_size",
            "trainer-learning-rate": "ref/manifest/trainer#manifest-field-trainer.learning_rate",
            "trainer-optimizer-type": "ref/manifest/trainer#manifest-field-trainer.optimizer.type",
            "trainer-early-stop": "ref/manifest/trainer#manifest-field-trainer.early_stop",
            "export": "ref/manifest/export",
            "export-targets": "ref/manifest/export#manifest-field-export.targets",
            "export-quantization": "ref/manifest/export#manifest-field-export.quantization",
            "export-formats": "ref/manifest/export#manifest-field-export.formats",
            "export-representative-samples": "ref/manifest/export#manifest-field-export.representative_samples",
            "export-test-windows": "ref/manifest/export#manifest-field-export.test_windows",
            "a-complete-example": "ref/manifest/index#a-complete-example",
        },
    },
    "reference/cli": {
        "to": "ref/cli",
        "anchors": {
            "cli-reference": "ref/cli",
            "by-task": "ref/cli#by-task",
            "exit-codes": "ref/cli#exit-codes",
            "options-shared-by-the-commands": "ref/cli#options-shared-by-the-commands",
            "caravan-validate": "ref/cli#cli-caravan-validate",
            "caravan-render": "ref/cli#cli-caravan-render",
            "caravan-build": "ref/cli#cli-caravan-build",
            "caravan-train": "ref/cli#cli-caravan-train",
            "caravan-quantize": "ref/cli#cli-caravan-quantize",
            "caravan-export": "ref/cli#cli-caravan-export",
            "caravan-templates": "ref/cli#cli-caravan-templates",
            "caravan-boards": "ref/cli#cli-caravan-boards",
        },
    },
    "reference/rules": {
        "to": "ref/rules",
        "anchors": {
            "rules": "ref/rules",
            "schema-version": "ref/rules#schema-version",
            "v-1": "ref/rules#rule-V-1",
            "v-2-retired": "ref/rules#rule-V-2",
            "templates-and-boards": "ref/rules#templates-and-boards",
            "t-1": "ref/rules#rule-T-1",
            "t-2": "ref/rules#rule-T-2",
            "b-1": "ref/rules#rule-B-1",
            "manifest-consistency": "ref/rules#manifest-consistency",
            "cf-1": "ref/rules#rule-CF-1",
            "cf-2": "ref/rules#rule-CF-2",
            "cf-3-retired": "ref/rules#rule-CF-3",
            "cf-4": "ref/rules#rule-CF-4",
            "cf-5-retired": "ref/rules#rule-CF-5",
            "cf-6": "ref/rules#rule-CF-6",
            "cf-7-retired": "ref/rules#rule-CF-7",
            "cf-8-retired": "ref/rules#rule-CF-8",
            "cf-9": "ref/rules#rule-CF-9",
            "cf-10-retired": "ref/rules#rule-CF-10",
            "cf-11": "ref/rules#rule-CF-11",
            "cf-12": "ref/rules#rule-CF-12",
            "cf-13": "ref/rules#rule-CF-13",
            "cf-14": "ref/rules#rule-CF-14",
            "cf-15": "ref/rules#rule-CF-15",
            "cf-16": "ref/rules#rule-CF-16",
            "cf-17": "ref/rules#rule-CF-17",
            "data": "ref/rules#data",
            "ds-1": "ref/rules#rule-DS-1",
            "ds-2": "ref/rules#rule-DS-2",
            "ds-3": "ref/rules#rule-DS-3",
            "ds-4": "ref/rules#rule-DS-4",
            "ds-5": "ref/rules#rule-DS-5",
            "ds-6": "ref/rules#rule-DS-6",
            "ds-7-reserved": "ref/rules#rule-DS-7",
            "ds-8": "ref/rules#rule-DS-8",
            "ds-9-retired": "ref/rules#rule-DS-9",
            "ds-10": "ref/rules#rule-DS-10",
            "ds-11": "ref/rules#rule-DS-11",
            "ds-12": "ref/rules#rule-DS-12",
            "ds-13": "ref/rules#rule-DS-13",
            "ds-14": "ref/rules#rule-DS-14",
            "ds-15": "ref/rules#rule-DS-15",
            "fit-check": "ref/rules#fit-check",
            "f-1": "ref/rules#rule-F-1",
            "quantization": "ref/rules#quantization",
            "q-1": "ref/rules#rule-Q-1",
            "q-2": "ref/rules#rule-Q-2",
            "q-3": "ref/rules#rule-Q-3",
            "q-4": "ref/rules#rule-Q-4",
            "q-5": "ref/rules#rule-Q-5",
            "export": "ref/rules#export",
            "x-1": "ref/rules#rule-X-1",
            "x-2": "ref/rules#rule-X-2",
            "x-3": "ref/rules#rule-X-3",
            "x-4": "ref/rules#rule-X-4",
            "x-5-reserved": "ref/rules#rule-X-5",
            "x-6": "ref/rules#rule-X-6",
            "board-descriptions": "ref/rules#board-descriptions",
            "e-1": "ref/rules#rule-E-1",
            "s-1": "ref/rules#rule-S-1",
            "informational": "ref/rules#informational",
            "d-1": "ref/rules#rule-D-1",
        },
    },
    "budgets": "ref/budgets",
    "manifest-changes": "ref/manifest-changes",
    "compatibility": "ref/compatibility",
    "board-runs/index": "ref/board-runs/index",
    # Older forwards, pointed at the final page rather than at another forward.
    "try-it": "intro/tutorial",
    "guides/own-project": "intro/tutorial02",
    # The owner's personal board came off the site. The forward stays because the address was
    # published; the stub is noindex and carries no content, so nothing a reader reads mentions it.
    "guides/lora32": "intro/tutorial03",
}
