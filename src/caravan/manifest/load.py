"""Reading a manifest: the one entry point, and the one place pydantic errors become findings.

The sequence is the one in ``specs/001-manifest-schema/data-model.md``: read, version check,
migrate, schema validation, template resolution, board resolution, cross-field rules. The
author's file is never written.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import UnionType
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from caravan.manifest._yaml import DocumentError, read_mapping
from caravan.manifest.errors import (
    ALL_RULES,
    RULE_DATASET_UNRESOLVED,
    RULE_UNKNOWN_SCHEMA_VERSION,
    Finding,
    Gate,
    Unresolved,
    dotted_path,
)
from caravan.manifest.migrate import (
    SchemaVersionRegistry,
    UnknownSchemaVersion,
)
from caravan.manifest.migrate import (
    default_registry as default_versions,
)
from caravan.manifest.schema import Manifest
from caravan.targets.registry import BoardRegistry
from caravan.targets.registry import default_registry as default_boards
from caravan.templates.registry import TemplateRegistry
from caravan.templates.registry import default_registry as default_templates

DATASET_UNRESOLVED_REASON = "not resolved in this stage"
DATASET_TERMS_UNVERIFIED_REASON = "not stated by the author; not verified by this tool"


@dataclass
class LoadOutcome:
    """Everything a command needs to report about one load."""

    manifest: Manifest | None = None
    findings: list[Finding] = field(default_factory=list)
    gates: list[Gate] = field(default_factory=list)
    unresolved: list[Unresolved] = field(default_factory=list)
    declared_version: str | None = None
    effective_version: str | None = None
    migrations_applied: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return self.manifest is not None and not self.findings


# --- schema introspection, so a message can list what is accepted ------------------------------


def _as_model(annotation: Any) -> type[BaseModel] | None:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    if get_origin(annotation) in (Union, UnionType):
        for arg in get_args(annotation):
            model = _as_model(arg)
            if model is not None:
                return model
    return None


def _model_at(root: type[BaseModel], location: tuple[Any, ...]) -> type[BaseModel] | None:
    current: type[BaseModel] | None = root
    for part in location:
        if current is None:
            return None
        if isinstance(part, int):
            continue
        info = current.model_fields.get(str(part))
        if info is None:
            return None
        current = _as_model(info.annotation)
    return current


def _find_field(root: type[BaseModel], name: str, prefix: str = "") -> str | None:
    """Where in the schema a field of this name does belong, if anywhere."""
    for field_name, info in root.model_fields.items():
        here = f"{prefix}{field_name}"
        if field_name == name:
            return here
        nested = _as_model(info.annotation)
        if nested is not None and nested is not root:
            found = _find_field(nested, name, f"{here}.")
            if found is not None:
                return found
    return None


def findings_from_validation_error(
    exc: PydanticValidationError, root: type[BaseModel] = Manifest
) -> list[Finding]:
    """Turn pydantic's errors into findings in the form FR-002 requires.

    No pydantic type name, module path or traceback ever reaches a message: those belong to exit
    code 3 alone.
    """
    findings: list[Finding] = []
    for error in exc.errors():
        kind = error["type"]
        context = error.get("ctx") or {}

        if kind in ALL_RULES:
            findings.append(
                Finding(
                    path=str(context.get("path") or dotted_path(error["loc"])),
                    problem=str(context.get("problem") or error["msg"]),
                    found=context.get("found"),
                    accepted=tuple(context.get("accepted") or ()),
                    rule=kind,
                )
            )
            continue

        location = error["loc"]
        path = dotted_path(location)

        if kind == "extra_forbidden":
            name = str(location[-1])
            parent = _model_at(root, location[:-1])
            accepted = tuple(parent.model_fields) if parent is not None else ()
            findings.append(
                Finding(
                    path=path,
                    problem="unknown field",
                    accepted=accepted,
                    near=name,
                    belongs_at=_find_field(root, name),
                )
            )
            continue

        if kind == "missing":
            findings.append(Finding(path=path, problem="this field is required but missing"))
            continue

        if kind in {"literal_error", "enum"}:
            expected = str(context.get("expected", "")).replace("'", "")
            accepted = tuple(
                part.strip() for part in expected.replace(" or ", ", ").split(",") if part.strip()
            )
            findings.append(
                Finding(
                    path=path,
                    problem="not one of the accepted values",
                    found=error.get("input"),
                    accepted=accepted,
                )
            )
            continue

        message = error["msg"]
        for prefix in ("Value error, ", "Assertion failed, "):
            message = message.removeprefix(prefix)
        findings.append(Finding(path=path, problem=message, found=error.get("input")))

    return findings


# --- the load sequence --------------------------------------------------------------------------


def load_manifest(
    path: Path,
    *,
    versions: SchemaVersionRegistry | None = None,
    templates: TemplateRegistry | None = None,
    boards: BoardRegistry | None = None,
) -> LoadOutcome:
    """Read, migrate and validate one manifest. Raises ``DocumentError`` if it cannot be parsed."""
    versions = versions or default_versions()
    templates = templates or default_templates()
    boards = boards or default_boards()

    data = read_mapping(path)
    outcome = LoadOutcome()

    try:
        migration = versions.migrate(data)
    except UnknownSchemaVersion as exc:
        outcome.declared_version = exc.declared
        outcome.findings.append(
            Finding(
                path="apiVersion",
                problem="unknown schema version",
                found=exc.declared,
                accepted=exc.known,
                rule=RULE_UNKNOWN_SCHEMA_VERSION,
            )
        )
        outcome.gates.append(Gate("schema-version", "fail", exc.declared))
        return outcome

    outcome.declared_version = migration.declared
    outcome.effective_version = migration.effective
    outcome.migrations_applied = migration.applied
    outcome.gates.append(
        Gate(
            "schema-version",
            "pass",
            f"{migration.declared} → {migration.effective}"
            if migration.applied
            else migration.declared,
        )
    )

    try:
        manifest = Manifest.model_validate(
            migration.data, context={"templates": templates, "boards": boards}
        )
    except PydanticValidationError as exc:
        outcome.findings.extend(findings_from_validation_error(exc))
        outcome.gates.append(Gate("schema", "fail"))
        return outcome

    outcome.manifest = manifest
    outcome.gates.extend(
        [
            Gate("schema", "pass"),
            Gate("template-parameters", "pass", manifest.model.template),
            Gate("targets", "pass", ", ".join(manifest.export.targets)),
            Gate("cross-field", "pass"),
        ]
    )

    # Recorded, never resolved: a valid manifest is not a resolved dataset (rule D-1).
    outcome.unresolved.append(
        Unresolved(
            kind="dataset-reference",
            value=manifest.dataset.source,
            reason=DATASET_UNRESOLVED_REASON,
            rule=RULE_DATASET_UNRESOLVED,
        )
    )
    # Silence about a licence stays visible as silence (FR-032, Principle VI).
    if manifest.dataset.permitted_use == "unknown":
        outcome.unresolved.append(
            Unresolved(
                kind="dataset-terms",
                value="unknown",
                reason=DATASET_TERMS_UNVERIFIED_REASON,
            )
        )
    return outcome


__all__ = [
    "DocumentError",
    "LoadOutcome",
    "findings_from_validation_error",
    "load_manifest",
]
