"""The manifest root and every rule that spans more than one field.

Field-level rules live with their section; the rules that relate two sections live here, because
that is the only place that can see both. Each one carries its identifier from
``specs/001-manifest-schema/data-model.md`` out to the finding, so a test asserts which rule fired
rather than matching prose.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationInfo, model_validator
from pydantic import ValidationError as PydanticValidationError

from caravan.manifest.errors import (
    RULE_CALIBRATION_SAMPLES,
    RULE_COLUMN_BOTH_WAYS,
    RULE_DECLARATION_NAME,
    RULE_DECLARATIONS_IMPLEMENTED,
    RULE_TEMPLATE_PARAMETERS,
    RULE_UNKNOWN_BOARD,
    RULE_UNKNOWN_TEMPLATE,
    RULE_WINDOW_MATCHES_TEMPLATE,
    dotted_path,
    rule_error,
)
from caravan.manifest.schema.dataset import MINIMUM_REPRESENTATIVE_SAMPLES, DatasetSpec, Split
from caravan.manifest.schema.export import ExportSpec
from caravan.manifest.schema.io import (
    INPUT_KINDS,
    OUTPUT_KINDS,
    InputDeclaration,
    OutputDeclaration,
    name_problem,
)
from caravan.manifest.schema.model import ModelSpec
from caravan.manifest.schema.train import TrainSpec
from caravan.manifest.version import SCHEMA_VERSION
from caravan.targets.registry import BoardRegistry
from caravan.targets.registry import default_registry as default_boards
from caravan.templates.registry import TemplateRegistry
from caravan.templates.registry import default_registry as default_templates

__all__ = [
    "DatasetSpec",
    "ExportSpec",
    "InputDeclaration",
    "Manifest",
    "ModelSpec",
    "OutputDeclaration",
    "Split",
    "TrainSpec",
]

#: Why a second input or output is refused, in the words the finding uses (rule CF-10).
SEVERAL_NOT_IMPLEMENTED = (
    "one input and one output are implemented; several arrive with the first named model or "
    "documented application that needs them (Principle X, "
    "docs/research/2026-10-23-multi-io-on-mcu.md)"
)


def _templates(info: ValidationInfo) -> TemplateRegistry:
    context = info.context or {}
    registry = context.get("templates")
    return registry if registry is not None else default_templates()


def _boards(info: ValidationInfo) -> BoardRegistry:
    context = info.context or {}
    registry = context.get("boards")
    return registry if registry is not None else default_boards()


class Manifest(BaseModel):
    """One file, one model version."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    # The wire name, deliberately not snake_case: it is what the manifest file says.
    apiVersion: Literal["caravan/v0.1"] = SCHEMA_VERSION
    model: ModelSpec
    inputs: list[InputDeclaration]
    outputs: list[OutputDeclaration]
    dataset: DatasetSpec
    train: TrainSpec = TrainSpec()
    export: ExportSpec

    # --- the declarations: CF-10, then CF-9, then CF-11 ---------------------------------------

    @model_validator(mode="after")
    def _one_of_each_and_kinds_implemented(self) -> Manifest:
        for section, declared in (("inputs", self.inputs), ("outputs", self.outputs)):
            if len(declared) != 1:
                rule_error(
                    RULE_DECLARATIONS_IMPLEMENTED,
                    section,
                    f"exactly one entry is accepted, found {len(declared)}: "
                    + SEVERAL_NOT_IMPLEMENTED,
                    found=len(declared),
                )
        for section, declared, kinds in (
            ("inputs", self.inputs, INPUT_KINDS),
            ("outputs", self.outputs, OUTPUT_KINDS),
        ):
            for index, declaration in enumerate(declared):
                if declaration.kind not in kinds:
                    rule_error(
                        RULE_DECLARATIONS_IMPLEMENTED,
                        f"{section}[{index}].kind",
                        f"this build implements the {section[:-1]} kind(s) {', '.join(kinds)}; "
                        "another kind arrives with the first named model or documented "
                        "application that needs it (Principle X)",
                        found=declaration.kind,
                        accepted=kinds,
                    )
        return self

    @model_validator(mode="after")
    def _names_are_well_formed_and_distinct(self) -> Manifest:
        seen: dict[str, str] = {}
        for section, declared in (("inputs", self.inputs), ("outputs", self.outputs)):
            for index, declaration in enumerate(declared):
                path = f"{section}[{index}].name"
                problem = name_problem(declaration.name)
                if problem is not None:
                    rule_error(RULE_DECLARATION_NAME, path, problem, found=declaration.name)
                if declaration.name in seen:
                    rule_error(
                        RULE_DECLARATION_NAME,
                        path,
                        f"the name is already used at {seen[declaration.name]}; a runner binds "
                        "inputs and outputs by name, so every name must be unique",
                        found=declaration.name,
                    )
                seen[declaration.name] = path
        return self

    @model_validator(mode="after")
    def _no_column_is_both_input_and_output(self) -> Manifest:
        answers = {output.column for output in self.outputs}
        for index, declaration in enumerate(self.inputs):
            both = sorted(answers & set(declaration.columns or ()))
            if both:
                rule_error(
                    RULE_COLUMN_BOTH_WAYS,
                    f"inputs[{index}].columns",
                    f"column {both[0]} is the output's answer and cannot also be an input: the "
                    "model would be trained on its own answer",
                    found=both,
                )
        return self

    # --- template resolution: T-1, then T-2, then CF-6 ---------------------------------------

    @model_validator(mode="after")
    def _template_is_registered(self, info: ValidationInfo) -> Manifest:
        registry = _templates(info)
        if registry.get(self.model.template) is None:
            rule_error(
                RULE_UNKNOWN_TEMPLATE,
                "model.template",
                "unknown template",
                found=self.model.template,
                accepted=registry.identifiers,
            )
        return self

    @model_validator(mode="after")
    def _template_parameters_are_valid(self, info: ValidationInfo) -> Manifest:
        spec = _templates(info).get(self.model.template)
        if spec is None:  # T-1 already reported it
            return self
        try:
            spec.parameters.model_validate(self.model.params)
        except PydanticValidationError as exc:
            first = exc.errors()[0]
            where = dotted_path(first["loc"]) if first["loc"] else ""
            message = first["msg"].removeprefix("Value error, ")
            rule_error(
                RULE_TEMPLATE_PARAMETERS,
                f"model.params.{where}" if where else "model.params",
                f"the {self.model.template} template rejects this parameter: {message}",
                found=first.get("input"),
            )
        return self

    @model_validator(mode="after")
    def _window_matches_template(self, info: ValidationInfo) -> Manifest:
        spec = _templates(info).get(self.model.template)
        if spec is None or len(self.inputs) != 1:
            return self
        window = self.inputs[0].window
        path = "inputs[0].window"
        if spec.consumes_window and window is None:
            rule_error(
                RULE_WINDOW_MATCHES_TEMPLATE,
                path,
                f"the {spec.identifier} template consumes a time window, so {path} must be set",
            )
        if not spec.consumes_window and window is not None:
            rule_error(
                RULE_WINDOW_MATCHES_TEMPLATE,
                path,
                f"the {spec.identifier} template does not consume a time window, so {path} "
                "must be left out",
                found=window,
            )
        # A window can be present and still be too short for what the parameters describe. Only the
        # template can tell — it knows what a kernel is and the core does not — so the core asks it
        # and reports whatever sentence comes back (feature 005, research R6). Asked after the
        # parameters have validated, because a check over invalid parameters would report the wrong
        # problem.
        if spec.window_fit is not None and spec.consumes_window and window is not None:
            try:
                params = spec.parameters.model_validate(self.model.params)
            except PydanticValidationError:
                return self  # T-2 above already reported it
            verdict = spec.window_fit(params, int(window))
            if verdict is not None:
                problem, accepted = verdict
                rule_error(
                    RULE_WINDOW_MATCHES_TEMPLATE,
                    path,
                    problem,
                    found=window,
                    accepted=accepted,
                )
        return self

    # --- board resolution: B-1 -----------------------------------------------------------------

    @model_validator(mode="after")
    def _targets_are_known(self, info: ValidationInfo) -> Manifest:
        registry = _boards(info)
        for index, target in enumerate(self.export.targets):
            if registry.get(target) is None:
                rule_error(
                    RULE_UNKNOWN_BOARD,
                    f"export.targets[{index}]",
                    "unknown board",
                    found=target,
                    accepted=registry.identifiers,
                )
        return self

    # --- quantization: CF-4 ---------------------------------------------------------------------

    @model_validator(mode="after")
    def _int8_needs_calibration_samples(self) -> Manifest:
        if self.export.quantization != "int8":
            return self
        samples = self.dataset.representative_samples
        if samples is None or samples < MINIMUM_REPRESENTATIVE_SAMPLES:
            rule_error(
                RULE_CALIBRATION_SAMPLES,
                "dataset.representative_samples",
                "int8 quantization calibrates against representative samples, so at least "
                f"{MINIMUM_REPRESENTATIVE_SAMPLES} are required",
                found=samples,
            )
        return self
