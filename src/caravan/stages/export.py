"""The export stage: the files a firmware author compiles, and the proof of what is in them.

Core module — the runtime import is inside the function, so importing this stage imports nothing
that installs separately.

Two things make this stage what it is. The operator set is read from the model file and never from
a runtime that loaded it, because the desktop interpreter reports a delegate node it inserted for
itself and a resolver built from that list would register a kernel the target has never heard of.
And the model it exports is the model the accuracy gate measured, byte for byte — the conversion
fixes the input batch (``caravan.convert.batch``), so there is one graph, one set of numbers, and
they describe what ships.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from caravan.env import (
    EnvironmentIncomplete,
    missing_runtime_message,
    model_runtime_available,
)
from caravan.export import c_array, interface, resolver, skeleton
from caravan.export import test_windows as windows
from caravan.export.artifacts import ExportSet, RunnerRequirements, record_artifact
from caravan.manifest.errors import (
    RULE_FORMAT_NOT_IMPLEMENTED,
    RULE_MULTIPLE_SUBGRAPHS,
    RULE_NOTHING_TO_EXPORT,
    run_rule_error,
)
from caravan.stages.base import StageContext, StageFunction, StageInputs, StageSpec
from caravan.stages.quantize import QUANTIZED_MODEL
from caravan.targets.kernels import coverage
from caravan.targets.registry import default_registry

#: The serialised model, written again under its own name. The run already holds the quantized
#: model, with identical bytes; the export set is what an author takes away, so it carries its own
#: copy beside the array and the resolver rather than a reference into another stage's output. The
#: report records both paths and their shared digest, so the duplication is visible rather than
#: accidental.
MODEL = "model/model.tflite"
MODEL_STEM = "model_data"
ARRAY_SOURCE = f"model/{MODEL_STEM}.cc"
ARRAY_HEADER = f"model/{MODEL_STEM}.h"
RESOLVER = f"model/{resolver.HEADER_NAME}"
RECORD = "export.json"
#: The test windows for a board (feature 009), written when ``export.test_windows`` is above 0.
TEST_WINDOWS = f"model/{windows.HEADER_NAME}"
#: The interface contract (feature 006, contracts/interface.md).
INTERFACE = "model/interface.json"

#: What this version can produce. ``onnx`` is in the schema because the roadmap still intends it;
#: a manifest asking for it is refused by name rather than silently given the other two.
IMPLEMENTED_FORMATS = ("flatbuffer", "c_array")


def runner_path(target: str) -> str:
    return f"runner/{target}/main.cc"


def _skeletons(inputs: StageInputs) -> tuple[str, ...]:
    """One runner skeleton per target the manifest names, and the test windows when asked for.

    Computed from the projection, so these files are declared as firmly as the fixed ones: a
    skeleton or a header the stage forgot to write fails the run rather than going missing from
    the export set.
    """
    skeletons = tuple(runner_path(target) for target in inputs["export.targets"])
    if inputs["export.test_windows"] > 0:
        return (*skeletons, TEST_WINDOWS)
    return skeletons


SPEC = StageSpec(
    name="export",
    reads=(
        "model.name",
        "model.version",
        "export.formats",
        "export.targets",
        "export.quantization",
        # For the interface contract (features 006, 008): which model, every input with what was
        # fitted for it, and what the output means. Never the budget: the quantize stage's key
        # already moves with it, and this stage's through its upstream.
        "input_features",
        "output_features[0].name",
        "output_features[0].type",
        "output_features[0].preprocessing",
        "output_features[0].threshold?",
        "output_features[0].clip?",
        "preprocessing.window_size",
        # For the test windows (feature 009): how many, and the split they are drawn from, formed
        # by the same code as the quantize stage's test part. Changing the count re-runs this
        # stage alone; nothing before it reads the field.
        "export.test_windows",
        "preprocessing.split",
        "random_seed",
    ),
    # Still false with the test windows of feature 009, although they are drawn from the data: the
    # quantize stage upstream reads the dataset, so its key — and through it this one — already
    # moves with every change to the data. Declaring it again would change nothing but the key's
    # text. The records are read only when windows are asked for.
    reads_dataset=False,
    upstream="quantize",
    artifacts=(MODEL, ARRAY_SOURCE, ARRAY_HEADER, RESOLVER, INTERFACE, RECORD),
    artifacts_from=_skeletons,
)


def require_parts(command: str) -> None:
    """Only the runtime that reads a model file. This stage converts nothing."""
    if not model_runtime_available():
        raise EnvironmentIncomplete(missing_runtime_message(command))


def check_formats(formats: list[str]) -> tuple[str, ...]:
    """Refuse X-1 before anything is written, for every format this version cannot produce.

    Before anything is written, and for *all* of them at once: a run that exported two of three
    requested formats and exited 0 would be the quiet half-success this project does not do.
    """
    unknown = [name for name in formats if name not in IMPLEMENTED_FORMATS]
    if unknown:
        run_rule_error(
            RULE_FORMAT_NOT_IMPLEMENTED,
            "export.formats",
            (
                f"export.formats names a format caravan cannot produce yet: {', '.join(unknown)}; "
                f"implemented: {', '.join(IMPLEMENTED_FORMATS)}. Nothing was written — remove the "
                "format or wait for the feature that adds it"
            ),
            found=list(formats),
        )
    return tuple(formats)


def load_model_bytes(run_dir: Path) -> bytes:
    """The quantized model of this run, or X-2 naming the stage that has to run first."""
    path = run_dir / QUANTIZED_MODEL
    if not path.is_file():
        run_rule_error(
            RULE_NOTHING_TO_EXPORT,
            "export.formats",
            (
                f"there is no quantized model in this run to export ({QUANTIZED_MODEL} is "
                "absent); run `caravan quantize` first, and note that a failed accuracy gate "
                "leaves nothing exportable"
            ),
            found=QUANTIZED_MODEL,
        )
    return path.read_bytes()


def check_single_subgraph(graph: Any) -> None:
    """Refuse X-3 rather than exporting one subgraph of several.

    A resolver for the first subgraph of several is wrong in a way nothing downstream would
    notice: the firmware would link kernels for one graph and the runtime would need another's.
    """
    if graph.subgraphs != 1:
        run_rule_error(
            RULE_MULTIPLE_SUBGRAPHS,
            "export.formats",
            (
                f"the model has {graph.subgraphs} subgraphs, and caravan exports a single-subgraph "
                "model; a resolver for one subgraph of several would link the wrong kernels"
            ),
            found=graph.subgraphs,
        )


def stage(context: StageContext) -> StageFunction:
    """The stage function. Reads a model file and board data; converts nothing."""

    def run(inputs: StageInputs, out_dir: Path) -> None:
        require_parts("export")

        from caravan.runtime.flatbuffer import FLOOR_METHOD, inspect_graph, read_bindings

        formats = check_formats(list(inputs["export.formats"]))
        targets = tuple(inputs["export.targets"])
        blob = load_model_bytes(context.run_dir)

        (out_dir / "model").mkdir(parents=True, exist_ok=True)
        model_path = out_dir / MODEL
        model_path.write_bytes(blob)

        graph = inspect_graph(model_path)
        check_single_subgraph(graph)

        exported = ExportSet(formats=formats, graph=graph)
        exported.artifacts.append(record_artifact(out_dir, MODEL, format="flatbuffer"))

        # The interface contract: every position read from the file, never from the manifest.
        features = inputs["input_features"]
        output = {
            "name": inputs["output_features[0].name"],
            "type": inputs["output_features[0].type"],
            "preprocessing": inputs["output_features[0].preprocessing"],
            "threshold": inputs.get("output_features[0].threshold"),
            "clip": inputs.get("output_features[0].clip"),
        }
        bindings = [
            binding.as_dict()
            for binding in read_bindings(
                model_path,
                inputs=[feature["name"] for feature in features],
                outputs=[output["name"]],
            )
        ]
        model_identity = {"name": inputs["model.name"], "version": inputs["model.version"]}
        (out_dir / INTERFACE).write_text(
            interface.interface_document(
                model_identity, bindings, features, output, inputs["preprocessing.window_size"]
            ),
            encoding="utf-8",
        )
        exported.artifacts.append(record_artifact(out_dir, INTERFACE, format="interface"))

        array_name = c_array.array_name(MODEL_STEM)
        (out_dir / ARRAY_SOURCE).write_text(
            c_array.source(MODEL_STEM, blob, interface.source_additions(array_name, output)),
            encoding="utf-8",
        )
        (out_dir / ARRAY_HEADER).write_text(
            c_array.header(
                MODEL_STEM,
                len(blob),
                interface.header_additions(array_name, model_identity, bindings, features, output),
            ),
            encoding="utf-8",
        )
        exported.artifacts.append(record_artifact(out_dir, ARRAY_SOURCE, format="c_array"))
        exported.artifacts.append(record_artifact(out_dir, ARRAY_HEADER, format="c_array"))

        (out_dir / RESOLVER).write_text(resolver.generate(graph.operators), encoding="utf-8")
        exported.artifacts.append(record_artifact(out_dir, RESOLVER, format="resolver"))

        input_bindings = [binding for binding in bindings if binding["role"] == "input"]
        output_binding = next(binding for binding in bindings if binding["role"] == "output")
        registry = default_registry()
        verdicts: list[Any] = []
        for target in targets:
            board = registry.get(target)
            if board is None:  # pragma: no cover - rule B-1 refuses an unknown board first
                continue
            target_verdicts = coverage(graph.operators, board)
            verdicts.extend(target_verdicts)
            accelerated = sum(1 for verdict in target_verdicts if verdict.accelerated)

            relative = runner_path(target)
            (out_dir / relative).parent.mkdir(parents=True, exist_ok=True)
            (out_dir / relative).write_text(
                skeleton.generate(
                    board=board,
                    graph=graph,
                    model_stem=MODEL_STEM,
                    array_name=c_array.array_name(MODEL_STEM),
                    accelerated=accelerated,
                    operators_total=len(graph.operators),
                    inputs=input_bindings,
                    output=output_binding,
                ),
                encoding="utf-8",
            )
            exported.artifacts.append(
                record_artifact(out_dir, relative, format="skeleton", target=target)
            )
            exported.requirements[target] = RunnerRequirements(
                runtime=board.toolchain.runtime,
                operators=tuple(operator.name for operator in graph.operators),
                working_memory_floor=graph.working_memory_floor,
                floor_method=FLOOR_METHOD,
            )

        exported.coverage = tuple(verdicts)
        written_windows = _write_test_windows(
            context, inputs, out_dir, model_path, array_name, bindings, output
        )
        if written_windows is not None:
            exported.artifacts.append(record_artifact(out_dir, TEST_WINDOWS, format="test_windows"))
        record = {
            **exported.as_dict(),
            "source_model": {
                "path": QUANTIZED_MODEL,
                "same_bytes_as": MODEL,
                "digest": exported.artifacts[0].digest,
            },
        }
        if written_windows is not None:
            record["test_windows"] = written_windows
        (out_dir / RECORD).write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

    return run


def _write_test_windows(
    context: StageContext,
    inputs: StageInputs,
    out_dir: Path,
    model_path: Path,
    array_name: str,
    bindings: list[dict[str, Any]],
    output: dict[str, Any],
) -> dict[str, Any] | None:
    """Write ``model/test_windows.h`` when the manifest asks for windows; its record, or None.

    The windows come from the test part the quantize stage measured — formed by the same function
    — and the host's answers from the quantized model this stage just exported, byte for byte.
    """
    count = int(inputs["export.test_windows"])
    if count == 0:
        return None

    from caravan import __version__
    from caravan.data.test_part import form_parts
    from caravan.stages.quantize import _runtime_version

    shaped = {
        **output,
        # The decision rule of a binary output needs the threshold the model was gated with.
        "threshold": output["threshold"] if output["threshold"] is not None else 0.5,
    }
    test_features, test_targets = form_parts(context.records(), inputs, shaped).test()
    record, chosen, expected, scores, decisions = windows.build(
        model_path=model_path,
        test_features=test_features,
        test_targets=test_targets,
        output=shaped,
        count=count,
    )
    provenance = {
        "model": f"{inputs['model.name']} {inputs['model.version']}",
        "run": context.run_id or context.run_dir.name,
        "dataset_version": context.dataset.version,
        "runtime": _runtime_version(),
        "caravan": __version__,
    }
    (out_dir / TEST_WINDOWS).write_text(
        windows.header(
            record=record,
            array_name=array_name,
            bindings=bindings,
            output=shaped,
            chosen=chosen,
            expected=expected,
            scores=scores,
            decisions=decisions,
            provenance=provenance,
        ),
        encoding="utf-8",
    )
    return record.as_dict()
