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
    RULE_EMULATOR_EXISTS,
    RULE_PERSONAL_DATA_RISK_CLASS,
    RULE_PUBLISH_BENCHMARK_ONLY,
    RULE_TEMPLATE_PARAMETERS,
    RULE_UNKNOWN_BOARD,
    RULE_UNKNOWN_TEMPLATE,
    RULE_WINDOW_MATCHES_TEMPLATE,
    dotted_path,
    rule_error,
)
from caravan.manifest.migrate import CURRENT_SCHEMA_VERSION
from caravan.manifest.schema.compliance import ComplianceSpec
from caravan.manifest.schema.dataset import MINIMUM_REPRESENTATIVE_SAMPLES, DatasetSpec, Split
from caravan.manifest.schema.export import ExportSpec
from caravan.manifest.schema.misc import BenchSpec, PublishSpec, VerifySpec
from caravan.manifest.schema.model import ModelSpec
from caravan.manifest.schema.train import TrainSpec
from caravan.targets.registry import BoardRegistry
from caravan.targets.registry import default_registry as default_boards
from caravan.templates.registry import TemplateRegistry
from caravan.templates.registry import default_registry as default_templates

__all__ = [
    "BenchSpec",
    "ComplianceSpec",
    "DatasetSpec",
    "ExportSpec",
    "Manifest",
    "ModelSpec",
    "PublishSpec",
    "Split",
    "TrainSpec",
    "VerifySpec",
]


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
    apiVersion: Literal["caravan/v0"] = CURRENT_SCHEMA_VERSION
    model: ModelSpec
    dataset: DatasetSpec
    train: TrainSpec = TrainSpec()
    export: ExportSpec
    verify: VerifySpec = VerifySpec()
    bench: BenchSpec = BenchSpec()
    publish: PublishSpec | None = None
    compliance: ComplianceSpec

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
        if spec.consumes_window and self.dataset.window is None:
            rule_error(
                RULE_WINDOW_MATCHES_TEMPLATE,
                "dataset.window",
                f"the {spec.identifier} template consumes a time window, so dataset.window "
                "must be set",
            )
        if not spec.consumes_window and self.dataset.window is not None:
            rule_error(
                RULE_WINDOW_MATCHES_TEMPLATE,
                "dataset.window",
                f"the {spec.identifier} template does not consume a time window, so "
                "dataset.window must be left out",
                found=self.dataset.window,
            )
        # A window can be present and still be too short for what the parameters describe. Only the
        # template can tell — it knows what a kernel is and the core does not — so the core asks it
        # and reports whatever sentence comes back (feature 005, research R6). Asked after the
        # parameters have validated, because a check over invalid parameters would report the wrong
        # problem.
        if spec.window_fit is not None and spec.consumes_window and self.dataset.window is not None:
            try:
                params = spec.parameters.model_validate(self.model.params)
            except PydanticValidationError:
                return self  # T-2 above already reported it
            verdict = spec.window_fit(params, int(self.dataset.window))
            if verdict is not None:
                problem, accepted = verdict
                rule_error(
                    RULE_WINDOW_MATCHES_TEMPLATE,
                    "dataset.window",
                    problem,
                    found=self.dataset.window,
                    accepted=accepted,
                )
        return self

    # --- board resolution: B-1, then CF-7 ------------------------------------------------------

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

    @model_validator(mode="after")
    def _emulator_exists_for_every_target(self, info: ValidationInfo) -> Manifest:
        if self.verify.emulator == "none":
            return self
        registry = _boards(info)
        without = [
            target
            for target in self.export.targets
            if (board := registry.get(target)) is not None and board.emulator is None
        ]
        if without:
            rule_error(
                RULE_EMULATOR_EXISTS,
                "verify.emulator",
                "these target boards have no emulator platform, so verification cannot name "
                f"one: {', '.join(without)}",
                found=self.verify.emulator,
                accepted=("none",),
            )
        return self

    # --- compliance and data terms: CF-3, CF-4, CF-8 -------------------------------------------

    @model_validator(mode="after")
    def _personal_data_is_not_minimal_risk(self) -> Manifest:
        if (
            self.compliance.privacy == "personal-data"
            and self.compliance.eu_ai_act_class == "minimal-risk"
        ):
            rule_error(
                RULE_PERSONAL_DATA_RISK_CLASS,
                "compliance.eu_ai_act_class",
                "a model that processes personal data (compliance.privacy) cannot be minimal-risk",
                found=self.compliance.eu_ai_act_class,
                accepted=("limited-risk", "high-risk"),
            )
        return self

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

    @model_validator(mode="after")
    def _benchmark_only_data_is_not_published(self) -> Manifest:
        # CF-8. The whole of what Caravan enforces about data rights: the author's own statement,
        # held to. An unstated term is never blocked, only marked unverified (Principle VI).
        if self.publish is not None and self.dataset.permitted_use == "benchmark-only":
            rule_error(
                RULE_PUBLISH_BENCHMARK_ONLY,
                "publish",
                "the author states that this dataset is not permitted for training "
                "(dataset.permitted_use), so a model built from it must not be published",
                found=self.dataset.permitted_use,
            )
        return self
