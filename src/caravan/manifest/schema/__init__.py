"""The manifest root and every rule that spans more than one field.

Field-level rules live with their section; the rules that relate two sections live here, because
that is the only place that can see both. Each one carries its identifier out to the finding, so a
test asserts which rule fired rather than matching prose.

Schema version ``caravan/v0.2`` (feature 008) names things as Ludwig does wherever Ludwig has the
concept: ``input_features``, ``output_features``, ``preprocessing``, ``defaults``, ``trainer`` and
``random_seed``. What Ludwig has no word for keeps Caravan's own: ``model`` (a microcontroller
architecture), ``dataset``, ``export`` and the int8 budgets (research R1).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, model_validator
from pydantic import ValidationError as PydanticValidationError

from caravan.manifest.errors import (
    RULE_BUDGET_FOR_TYPE,
    RULE_CALIBRATION_SAMPLES,
    RULE_COLUMN_BOTH_WAYS,
    RULE_DECLARATION_NAME,
    RULE_FEATURE_TYPE,
    RULE_ONE_OUTPUT,
    RULE_SPLIT_COLUMN_DECLARED,
    RULE_STRATIFY_COLUMN,
    RULE_TEMPLATE_PARAMETERS,
    RULE_UNKNOWN_BOARD,
    RULE_UNKNOWN_TEMPLATE,
    RULE_WINDOW_MATCHES_TEMPLATE,
    dotted_path,
    field_error,
    rule_error,
)
from caravan.manifest.schema.export import MINIMUM_REPRESENTATIVE_SAMPLES, ExportSpec
from caravan.manifest.schema.features import (
    INPUT_TYPES,
    OUTPUT_KEYS,
    OUTPUT_TYPES,
    Encoder,
    InputFeature,
    InputPreprocessing,
    OutputFeature,
    input_key_problem,
    name_problem,
)
from caravan.manifest.schema.model import ModelSpec
from caravan.manifest.schema.preprocessing import GlobalPreprocessing, Split
from caravan.manifest.schema.trainer import TrainerSpec
from caravan.manifest.version import SCHEMA_VERSION
from caravan.targets.registry import BoardRegistry
from caravan.targets.registry import default_registry as default_boards
from caravan.templates.registry import TemplateRegistry
from caravan.templates.registry import default_registry as default_templates

__all__ = [
    "ExportSpec",
    "GlobalPreprocessing",
    "InputFeature",
    "Manifest",
    "ModelSpec",
    "OutputFeature",
    "Split",
    "TrainerSpec",
    "TypeDefaults",
]

#: Why a type is not implemented, in the words the finding uses (rule CF-14).
TYPE_NOT_IMPLEMENTED = (
    "each type brings its preprocessing into the model, and only types with a path to the "
    "microcontroller are implemented; another type arrives with the first named model or "
    "documented application that needs it (Principle X, "
    "docs/research/2026-10-24-typed-features-on-mcu.md)"
)


def _templates(info: ValidationInfo) -> TemplateRegistry:
    context = info.context or {}
    registry = context.get("templates")
    return registry if registry is not None else default_templates()


def _boards(info: ValidationInfo) -> BoardRegistry:
    context = info.context or {}
    registry = context.get("boards")
    return registry if registry is not None else default_boards()


class TypeDefaults(BaseModel):
    """What every input feature of one type gets unless it states its own (Ludwig's ``defaults``)."""

    model_config = ConfigDict(extra="forbid")

    preprocessing: InputPreprocessing = Field(default_factory=InputPreprocessing)
    encoder: Encoder | None = None


class Manifest(BaseModel):
    """One file, one model version."""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    # The wire name, deliberately not snake_case: it is what the manifest file says.
    apiVersion: Literal["caravan/v0.2"] = SCHEMA_VERSION
    model: ModelSpec
    input_features: list[InputFeature] = Field(min_length=1)
    output_features: list[OutputFeature]
    preprocessing: GlobalPreprocessing = Field(default_factory=GlobalPreprocessing)
    defaults: dict[str, TypeDefaults] = Field(default_factory=dict)
    #: The directory or file of the data, relative to the manifest.
    dataset: str = Field(min_length=1)
    trainer: TrainerSpec = Field(default_factory=TrainerSpec)
    #: Seeds the split, the calibration sample and training (Principle III).
    random_seed: int = 42
    export: ExportSpec

    # --- the features: CF-17, CF-14, keys per type, CF-16, CF-9, CF-11 --------------------------

    @model_validator(mode="after")
    def _exactly_one_output(self) -> Manifest:
        if len(self.output_features) != 1:
            rule_error(
                RULE_ONE_OUTPUT,
                "output_features",
                f"exactly one output feature is accepted, found {len(self.output_features)}; "
                "several arrive with the first named model or documented application that needs "
                "them (Principle X)",
                found=len(self.output_features),
            )
        return self

    @model_validator(mode="after")
    def _types_are_implemented(self) -> Manifest:
        for index, feature in enumerate(self.input_features):
            if feature.type not in INPUT_TYPES:
                rule_error(
                    RULE_FEATURE_TYPE,
                    f"input_features[{index}].type",
                    f"this build implements the input types {', '.join(INPUT_TYPES)}; "
                    + TYPE_NOT_IMPLEMENTED,
                    found=feature.type,
                    accepted=INPUT_TYPES,
                )
        output = self.output_features[0]
        if output.type not in OUTPUT_TYPES:
            rule_error(
                RULE_FEATURE_TYPE,
                "output_features[0].type",
                f"this build implements the output types {', '.join(OUTPUT_TYPES)}; "
                + TYPE_NOT_IMPLEMENTED,
                found=output.type,
                accepted=OUTPUT_TYPES,
            )
        for key in sorted(self.defaults):
            if key not in INPUT_TYPES:
                rule_error(
                    RULE_FEATURE_TYPE,
                    f"defaults.{key}",
                    f"defaults are given per input type, and this build implements "
                    f"{', '.join(INPUT_TYPES)}; " + TYPE_NOT_IMPLEMENTED,
                    found=key,
                    accepted=INPUT_TYPES,
                )
        return self

    @model_validator(mode="after")
    def _keys_apply_to_their_type(self) -> Manifest:
        for index, feature in enumerate(self.input_features):
            problem = input_key_problem(feature.type, feature.preprocessing, feature.encoder)
            if problem is not None:
                where, what = problem
                field_error(f"input_features[{index}].{where}", what)
        for key, entry in sorted(self.defaults.items()):
            problem = input_key_problem(key, entry.preprocessing, entry.encoder)
            if problem is not None:
                where, what = problem
                field_error(f"defaults.{key}.{where}", what)
        output = self.output_features[0]
        for key in output.stated_keys():
            applies = OUTPUT_KEYS[key]
            if output.type in applies or key in ("accuracy_drop_max", "mae_increase_max"):
                continue
            field_error(
                f"output_features[0].{key}",
                f"does not apply to a {output.type} output; it applies to {' and '.join(applies)}",
            )
        return self

    @model_validator(mode="after")
    def _budget_matches_the_output(self) -> Manifest:
        # CF-16: Principle V requires every manifest to state its int8 budget, in the metric of
        # its output: accuracy for a class, the mean absolute error for a number.
        output = self.output_features[0]
        wanted = "mae_increase_max" if output.type == "number" else "accuracy_drop_max"
        other = "accuracy_drop_max" if wanted == "mae_increase_max" else "mae_increase_max"
        if getattr(output, other) is not None:
            rule_error(
                RULE_BUDGET_FOR_TYPE,
                f"output_features[0].{other}",
                f"a {output.type} output states its int8 budget as {wanted}, in "
                + (
                    "the column's unit"
                    if wanted == "mae_increase_max"
                    else "accuracy lost to quantization"
                ),
                found=getattr(output, other),
                accepted=(wanted,),
            )
        if getattr(output, wanted) is None:
            rule_error(
                RULE_BUDGET_FOR_TYPE,
                f"output_features[0].{wanted}",
                f"a {output.type} output must state its int8 budget as {wanted} (Principle V)",
                accepted=(wanted,),
            )
        return self

    @model_validator(mode="after")
    def _names_are_well_formed_and_distinct(self) -> Manifest:
        seen: dict[str, str] = {}
        for section, features in (
            ("input_features", self.input_features),
            ("output_features", self.output_features),
        ):
            for index, feature in enumerate(features):
                path = f"{section}[{index}].name"
                problem = name_problem(feature.name)
                if problem is not None:
                    rule_error(RULE_DECLARATION_NAME, path, problem, found=feature.name)
                if feature.name in seen:
                    if section == "output_features":
                        # CF-11: an input reading the output's column is a model trained on its
                        # own answer, which is worse than a duplicate.
                        rule_error(
                            RULE_COLUMN_BOTH_WAYS,
                            seen[feature.name],
                            f"column {feature.name} is the output's answer and cannot also be an "
                            "input: the model would be trained on its own answer",
                            found=feature.name,
                        )
                    rule_error(
                        RULE_DECLARATION_NAME,
                        path,
                        f"the name is already used at {seen[feature.name]}; one feature reads one "
                        "column, and a runner binds every input by its name",
                        found=feature.name,
                    )
                seen[feature.name] = path
        return self

    # --- the split: CF-13, CF-15 ----------------------------------------------------------------

    @model_validator(mode="after")
    def _split_column(self) -> Manifest:
        split = self.preprocessing.split
        output = self.output_features[0]
        if split.type == "stratify":
            column = split.column if split.column is not None else output.name
            if column != output.name or output.type == "number":
                rule_error(
                    RULE_STRATIFY_COLUMN,
                    "preprocessing.split.column",
                    "a stratified split draws per class of the output, so its column is the "
                    f"output's ({output.name}) and the output is a category or binary; another "
                    "column is not implemented",
                    found=column,
                    accepted=() if output.type == "number" else (output.name,),
                )
        if split.type == "fixed" and split.column is not None:
            column = split.column
            if column == output.name:
                rule_error(
                    RULE_SPLIT_COLUMN_DECLARED,
                    "preprocessing.split.column",
                    f"column {column} is the output's answer and cannot also say where a record "
                    "belongs",
                    found=column,
                )
            if any(feature.name == column for feature in self.input_features):
                rule_error(
                    RULE_SPLIT_COLUMN_DECLARED,
                    "preprocessing.split.column",
                    f"column {column} is an input feature; the column that says where a record "
                    "belongs must not be something the model learns from",
                    found=column,
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
        if spec is None:
            return self
        window = self.preprocessing.window_size
        path = "preprocessing.window_size"
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
        # template can tell, so the core asks it and reports whatever sentence comes back (feature
        # 005, research R6), after the parameters have validated.
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
        samples = self.export.representative_samples
        if samples is None or samples < MINIMUM_REPRESENTATIVE_SAMPLES:
            rule_error(
                RULE_CALIBRATION_SAMPLES,
                "export.representative_samples",
                "int8 quantization calibrates against representative samples, so at least "
                f"{MINIMUM_REPRESENTATIVE_SAMPLES} are required",
                found=samples,
            )
        return self
