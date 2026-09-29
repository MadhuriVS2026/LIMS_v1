"""
Domain calculation engine for analytical test templates.

Replaces the R&D Analytical Development team's Excel calculation workbooks with
a safe, deterministic, side-effect-free expression evaluator plus the shared
analytical primitives those sheets rely on (dilution-factor chains, replicate
statistics, cumulative bracketing-standard pooling, regression).

Public surface:
    - `evaluate(expression, context)` — evaluate one formula expression.
    - `ExpressionError` — raised for malformed expressions.
    - `DilutionChain` — ordered (aliquot, diluted_to) volume steps.
    - `EMPTY` — the engine's blank/no-result sentinel, mirroring Excel's
      `IFERROR(..., "")` behaviour used throughout the source sheets.
"""
from src.domain.services.calculation.dilution import DilutionChain, DilutionStep
from src.domain.services.calculation.evaluator import (
    CriterionResult,
    EvaluationError,
    WorksheetEvaluator,
    WorksheetResult,
)
from src.domain.services.calculation.expression import (
    EMPTY,
    Empty,
    ExpressionError,
    evaluate,
    referenced_names,
)
from src.domain.services.calculation.template_schema import (
    CriterionDef,
    FieldDef,
    FieldKind,
    GroupDef,
    GroupKind,
    Operator,
    RoundMode,
    Rounding,
    RowSpec,
    Severity,
    TemplateDefinition,
    TemplateSchemaError,
    ValueType,
)

__all__ = [
    "CriterionDef",
    "CriterionResult",
    "DilutionChain",
    "DilutionStep",
    "EMPTY",
    "Empty",
    "EvaluationError",
    "ExpressionError",
    "FieldDef",
    "FieldKind",
    "GroupDef",
    "GroupKind",
    "Operator",
    "RoundMode",
    "Rounding",
    "RowSpec",
    "Severity",
    "TemplateDefinition",
    "TemplateSchemaError",
    "ValueType",
    "WorksheetEvaluator",
    "WorksheetResult",
    "evaluate",
    "referenced_names",
]
