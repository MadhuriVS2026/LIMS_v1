"""
Typed model for a test-template definition.

A template definition is stored as JSON so templates are configuration rather
than code, but it is parsed into these dataclasses before use so a malformed
definition fails loudly at load time instead of producing wrong numbers at
calculation time.

Structure:

    definition
      ├── context[]      fields auto-populated from TRF / product / session
      ├── flags[]        template-level switches (rrf_mode, unit_basis, ...)
      ├── groups[]       the body of the sheet
      │     ├── kind=singleton   one implicit row (e.g. sample-prep header)
      │     ├── kind=table       N repeating rows (standards, samples, impurities)
      │     └── kind=sequence    ordered rows with access to earlier rows
      │                          (dissolution timepoints)
      └── criteria[]     acceptance / system-suitability limits
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TemplateSchemaError(ValueError):
    """Raised when a template definition is structurally invalid."""


class GroupKind(str, Enum):
    SINGLETON = "singleton"
    TABLE = "table"
    SEQUENCE = "sequence"


class FieldKind(str, Enum):
    CONTEXT = "context"
    INPUT = "input"
    AREA = "area"
    CALCULATED = "calculated"
    FLAG = "flag"


class ValueType(str, Enum):
    NUMBER = "number"
    TEXT = "text"
    DATE = "date"
    BOOLEAN = "boolean"


class RoundMode(str, Enum):
    NONE = "none"
    ROUND = "round"
    TRUNC = "trunc"


class Severity(str, Enum):
    BLOCKING = "blocking"
    ADVISORY = "advisory"


class Operator(str, Enum):
    LTE = "lte"  # not more than
    GTE = "gte"  # not less than
    BETWEEN = "between"
    EQ = "eq"


_IDENT_RESERVED = {"row", "prev", "prior", "index", "rowno"}


def _require(mapping: dict, key: str, where: str) -> Any:
    if key not in mapping:
        raise TemplateSchemaError(f"{where}: missing required key {key!r}")
    return mapping[key]


def _enum(enum_cls, value: Any, where: str):
    try:
        return enum_cls(value)
    except ValueError:
        allowed = ", ".join(e.value for e in enum_cls)
        raise TemplateSchemaError(
            f"{where}: {value!r} is not a valid {enum_cls.__name__} (allowed: {allowed})"
        ) from None


@dataclass(frozen=True)
class Rounding:
    mode: RoundMode = RoundMode.NONE
    digits: int = 0
    #  Where the sheet exposes the digit count as an analyst input, the field
    #  key holding it goes here and overrides `digits` at evaluation time.
    digits_from: str | None = None

    @classmethod
    def parse(cls, raw: dict | None, where: str) -> "Rounding":
        if not raw:
            return cls()
        mode = _enum(RoundMode, raw.get("mode", "none"), f"{where}.rounding.mode")
        digits = raw.get("digits", 0)
        if not isinstance(digits, int):
            raise TemplateSchemaError(f"{where}.rounding.digits must be an integer")
        return cls(mode=mode, digits=digits, digits_from=raw.get("digitsFrom"))


@dataclass(frozen=True)
class FieldDef:
    key: str
    kind: FieldKind
    label: str = ""
    type: ValueType = ValueType.NUMBER
    unit: str | None = None
    #  CALCULATED only
    expression: str | None = None
    rounding: Rounding = field(default_factory=Rounding)
    #  INPUT / AREA
    required: bool = False
    default: Any = None
    options: tuple[str, ...] = ()
    #  CONTEXT: dotted path into the context payload (e.g. "trf.batch_number")
    source: str | None = None
    overridable: bool = False
    #  AREA: where the value came from; the Waters import will set CDS_IMPORT.
    area_source: str = "ManualEntry"

    @classmethod
    def parse(cls, raw: dict, where: str) -> "FieldDef":
        key = _require(raw, "key", where)
        if not isinstance(key, str) or not key.isidentifier():
            raise TemplateSchemaError(f"{where}: field key {key!r} must be a valid identifier")
        if key in _IDENT_RESERVED:
            raise TemplateSchemaError(f"{where}: field key {key!r} is reserved")

        kind = _enum(FieldKind, _require(raw, "kind", where), f"{where}.kind")
        expression = raw.get("expression")
        if kind is FieldKind.CALCULATED and not expression:
            raise TemplateSchemaError(f"{where}: calculated field {key!r} needs an 'expression'")
        if kind is not FieldKind.CALCULATED and expression:
            raise TemplateSchemaError(
                f"{where}: field {key!r} is {kind.value} but declares an expression"
            )

        options = raw.get("options") or ()
        if not isinstance(options, (list, tuple)):
            raise TemplateSchemaError(f"{where}: field {key!r} 'options' must be a list")

        return cls(
            key=key,
            kind=kind,
            label=raw.get("label") or key,
            type=_enum(ValueType, raw.get("type", "number"), f"{where}.type"),
            unit=raw.get("unit"),
            expression=expression,
            rounding=Rounding.parse(raw.get("rounding"), f"{where}[{key}]"),
            required=bool(raw.get("required", False)),
            default=raw.get("default"),
            options=tuple(str(o) for o in options),
            source=raw.get("source"),
            overridable=bool(raw.get("overridable", False)),
            area_source=raw.get("areaSource", "ManualEntry"),
        )

    @property
    def is_editable(self) -> bool:
        """Analyst-editable on the worksheet."""
        return self.kind in (FieldKind.INPUT, FieldKind.AREA) or (
            self.kind is FieldKind.CONTEXT and self.overridable
        )


@dataclass(frozen=True)
class RowSpec:
    min: int = 1
    max: int = 1
    default: int = 1
    #  Rows may be labelled from one of their own fields (e.g. analyte name).
    label_from: str | None = None

    @classmethod
    def parse(cls, raw: dict | None, where: str) -> "RowSpec":
        if not raw:
            return cls()
        min_ = raw.get("min", 1)
        max_ = raw.get("max", min_)
        default = raw.get("default", min_)
        for name, value in (("min", min_), ("max", max_), ("default", default)):
            if not isinstance(value, int) or value < 0:
                raise TemplateSchemaError(f"{where}.rows.{name} must be a non-negative integer")
        if max_ < min_:
            raise TemplateSchemaError(f"{where}.rows: max ({max_}) is less than min ({min_})")
        if not (min_ <= default <= max_):
            raise TemplateSchemaError(
                f"{where}.rows: default ({default}) is outside min..max ({min_}..{max_})"
            )
        return cls(min=min_, max=max_, default=default, label_from=raw.get("labelFrom"))


@dataclass(frozen=True)
class GroupDef:
    key: str
    kind: GroupKind
    label: str = ""
    rows: RowSpec = field(default_factory=RowSpec)
    fields: tuple[FieldDef, ...] = ()

    @classmethod
    def parse(cls, raw: dict, where: str) -> "GroupDef":
        key = _require(raw, "key", where)
        if not isinstance(key, str) or not key.isidentifier():
            raise TemplateSchemaError(f"{where}: group key {key!r} must be a valid identifier")

        kind = _enum(GroupKind, _require(raw, "kind", where), f"{where}.kind")
        raw_fields = _require(raw, "fields", where)
        if not isinstance(raw_fields, list) or not raw_fields:
            raise TemplateSchemaError(f"{where}: group {key!r} needs a non-empty 'fields' list")

        fields_parsed = tuple(
            FieldDef.parse(f, f"{where}.groups[{key}].fields[{i}]") for i, f in enumerate(raw_fields)
        )
        seen: set[str] = set()
        for f in fields_parsed:
            if f.key in seen:
                raise TemplateSchemaError(f"{where}: group {key!r} has duplicate field {f.key!r}")
            seen.add(f.key)

        rows = RowSpec.parse(raw.get("rows"), f"{where}.groups[{key}]")
        if kind is GroupKind.SINGLETON and (rows.min, rows.max) != (1, 1):
            rows = RowSpec(min=1, max=1, default=1, label_from=rows.label_from)

        if rows.label_from and rows.label_from not in seen:
            raise TemplateSchemaError(
                f"{where}: group {key!r} labelFrom {rows.label_from!r} is not one of its fields"
            )

        return cls(key=key, kind=kind, label=raw.get("label") or key, rows=rows, fields=fields_parsed)

    def field(self, key: str) -> FieldDef | None:
        return next((f for f in self.fields if f.key == key), None)

    @property
    def is_multi_row(self) -> bool:
        return self.kind in (GroupKind.TABLE, GroupKind.SEQUENCE)


@dataclass(frozen=True)
class CriterionDef:
    key: str
    label: str
    target: str  # expression yielding the observed value
    operator: Operator
    limit: tuple[float, ...]
    severity: Severity = Severity.BLOCKING
    limit_text: str = ""

    @classmethod
    def parse(cls, raw: dict, where: str) -> "CriterionDef":
        key = _require(raw, "key", where)
        operator = _enum(Operator, _require(raw, "operator", where), f"{where}.operator")
        raw_limit = _require(raw, "limit", where)
        limit = tuple(float(x) for x in raw_limit) if isinstance(raw_limit, (list, tuple)) else (float(raw_limit),)

        if operator is Operator.BETWEEN and len(limit) != 2:
            raise TemplateSchemaError(f"{where}: 'between' criterion {key!r} needs two limits")
        if operator is not Operator.BETWEEN and len(limit) != 1:
            raise TemplateSchemaError(f"{where}: criterion {key!r} needs exactly one limit")

        return cls(
            key=key,
            label=raw.get("label") or key,
            target=_require(raw, "target", where),
            operator=operator,
            limit=limit,
            severity=_enum(Severity, raw.get("severity", "blocking"), f"{where}.severity"),
            limit_text=raw.get("limitText") or "",
        )


@dataclass(frozen=True)
class TemplateDefinition:
    """The parsed, validated body of a test template."""

    context: tuple[FieldDef, ...] = ()
    groups: tuple[GroupDef, ...] = ()
    criteria: tuple[CriterionDef, ...] = ()
    #  Dotted `group.field` reference to the reportable result.
    result_ref: str | None = None

    @classmethod
    def parse(cls, raw: dict | None) -> "TemplateDefinition":
        if not raw:
            return cls()
        if not isinstance(raw, dict):
            raise TemplateSchemaError("definition must be an object")

        where = "definition"

        raw_context = raw.get("context") or []
        if not isinstance(raw_context, list):
            raise TemplateSchemaError(f"{where}.context must be a list")
        context = tuple(
            FieldDef.parse(c, f"{where}.context[{i}]") for i, c in enumerate(raw_context)
        )

        raw_groups = raw.get("groups") or []
        if not isinstance(raw_groups, list):
            raise TemplateSchemaError(f"{where}.groups must be a list")
        groups = tuple(GroupDef.parse(g, where) for g in raw_groups)

        group_keys: set[str] = set()
        for g in groups:
            if g.key in group_keys:
                raise TemplateSchemaError(f"{where}: duplicate group key {g.key!r}")
            group_keys.add(g.key)

        context_keys = {c.key for c in context}
        clash = context_keys & group_keys
        if clash:
            raise TemplateSchemaError(
                f"{where}: {sorted(clash)} used as both a context field and a group key"
            )

        raw_criteria = raw.get("criteria") or []
        if not isinstance(raw_criteria, list):
            raise TemplateSchemaError(f"{where}.criteria must be a list")
        criteria = tuple(
            CriterionDef.parse(c, f"{where}.criteria[{i}]") for i, c in enumerate(raw_criteria)
        )

        definition = cls(
            context=context,
            groups=groups,
            criteria=criteria,
            result_ref=raw.get("resultRef"),
        )
        definition._validate_result_ref()
        return definition

    def _validate_result_ref(self) -> None:
        if self.result_ref is None:
            return
        parts = self.result_ref.split(".")
        if len(parts) != 2:
            raise TemplateSchemaError(
                f"definition.resultRef {self.result_ref!r} must be 'group.field'"
            )
        group = self.group(parts[0])
        if group is None or group.field(parts[1]) is None:
            raise TemplateSchemaError(
                f"definition.resultRef {self.result_ref!r} does not resolve to a template field"
            )

    def group(self, key: str) -> GroupDef | None:
        return next((g for g in self.groups if g.key == key), None)

    def context_field(self, key: str) -> FieldDef | None:
        return next((c for c in self.context if c.key == key), None)

    @property
    def area_field_refs(self) -> tuple[tuple[str, str], ...]:
        """Every `(group_key, field_key)` that holds a chromatographic area.

        Used by the future Waters import to know what it can populate without
        the adapter needing to understand any individual template.
        """
        return tuple(
            (g.key, f.key)
            for g in self.groups
            for f in g.fields
            if f.kind is FieldKind.AREA
        )
