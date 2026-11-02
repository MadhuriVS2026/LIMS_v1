"""Render calculated unknown-impurity totals directly below their table.

Adds two spreadsheet-style footer rows to the active TPL-A4-0003 v1 unknown
impurity calculation section. Values are computed from the existing summary
fields and land under % Impurity and Reporting % Impurity, matching the source
worksheet layout.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from _apply_a4_known_impurity_calculation import (
    source_example_values,
    validate_source_example,
)
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

DB = Path("lims.db")
CODE = "TPL-A4-0003"
VERSION = 1
ACTOR = "kiro-a4unknownfooter"

TABLE_FOOTER_ROWS = [
    {
        "label": "Single maximum unknown impurity",
        "labelColSpan": 6,
        "values": {
            "pct": {
                "ref": "summary.max_single_unknown",
                "rounding": {"mode": "round", "digits": 4},
            },
            "reported": {
                "ref": "summary.max_single_unknown_reported",
                "rounding": {"mode": "round", "digits": 3},
            },
        },
    },
    {
        "label": "Total unknown impurities",
        "labelColSpan": 6,
        "values": {
            "pct": {
                "ref": "summary.total_unknowns",
                "rounding": {"mode": "round", "digits": 4},
            },
            "reported": {
                "ref": "summary.total_unknowns_reported",
                "rounding": {"mode": "round", "digits": 3},
            },
        },
    },
]

UNKNOWN_SUMMARY_KEYS = {
    "max_single_unknown",
    "max_single_unknown_reported",
    "total_unknowns",
    "total_unknowns_reported",
}


def proposed_definition(raw_definition: str) -> dict:
    definition = json.loads(raw_definition)
    groups = {group.get("key"): group for group in definition.get("groups", [])}
    impurities = groups.get("impurities")
    summary = groups.get("summary")
    if impurities is None or summary is None:
        raise RuntimeError("Impurity Calculation or Impurity Summary group is missing")
    if impurities.get("tableFooterRows"):
        raise RuntimeError("Unknown-impurity table footer already exists")
    visible = [field.get("key") for field in impurities.get("fields", []) if not field.get("hidden")]
    expected_columns = ["name", "rt", "area", "loq", "rrf", "rrt", "pct", "reported"]
    if visible != expected_columns:
        raise RuntimeError(f"Unexpected unknown-impurity columns: {visible}")

    summary_fields = {field.get("key"): field for field in summary.get("fields", [])}
    if not UNKNOWN_SUMMARY_KEYS.issubset(summary_fields):
        raise RuntimeError("Unknown-impurity summary fields are incomplete")

    impurities["tableFooterRows"] = TABLE_FOOTER_ROWS
    for key in UNKNOWN_SUMMARY_KEYS:
        summary_fields[key]["hidden"] = True
    return definition


def backup_database() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"lims.db.bak-a4unknownfooter-{stamp}")
    with sqlite3.connect(DB) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    return backup


def main() -> int:
    if not DB.is_file():
        print(f"ERROR: {DB} does not exist")
        return 1

    validate_only = "--validate-only" in sys.argv
    con = sqlite3.connect(DB, timeout=30)
    try:
        template = con.execute(
            "select id, code, archetype, version, status, test_id, definition "
            "from test_templates where code=? and version=? and status=?",
            (CODE, VERSION, "Active"),
        ).fetchone()
        if template is None:
            raise RuntimeError(f"Active {CODE} v{VERSION} was not found")

        template_id, code, archetype, version, status, test_id, raw_definition = template
        definition = proposed_definition(raw_definition)
        parsed = TemplateDefinition.parse(definition)
        evaluator = WorksheetEvaluator(parsed)
        impurities = next(group for group in definition["groups"] if group.get("key") == "impurities")
        context, source_values = source_example_values(impurities["rows"]["seed"])
        validate_source_example(evaluator, impurities["rows"]["seed"])
        source_result = evaluator.evaluate(context, source_values)
        if source_result.values["summary.max_single_unknown"] != 0.0647:
            raise RuntimeError("Source maximum unknown impurity did not calculate to 0.0647")
        if source_result.values["summary.max_single_unknown_reported"] != 0.065:
            raise RuntimeError("Source maximum unknown reporting result did not calculate to 0.065")
        if source_result.values["summary.total_unknowns"] != 0.076:
            raise RuntimeError("Source total unknown impurities did not calculate to 0.0760")
        if source_result.values["summary.total_unknowns_reported"] != 0.065:
            raise RuntimeError("Source total unknown reporting result did not calculate to 0.065")

        worksheets = con.execute(
            "select id, context_values, group_values from test_worksheets "
            "where template_id=? and template_version=? and status=? order by id",
            (template_id, VERSION, "InProgress"),
        ).fetchall()
        for worksheet_id, raw_context, raw_values in worksheets:
            try:
                evaluator.evaluate(json.loads(raw_context or "{}"), json.loads(raw_values or "{}"))
            except Exception as exc:
                raise RuntimeError(f"Worksheet {worksheet_id} failed after footer update: {exc}") from exc

        if validate_only:
            print(f"valid={CODE} v{VERSION}; table_footer_rows={len(TABLE_FOOTER_ROWS)}")
            print("source_example=max=0.0647/0.065; total=0.0760/0.065")
            print(f"validated_in_progress_worksheets={len(worksheets)}")
            return 0

        backup = backup_database()
        now = datetime.now().isoformat(timespec="seconds")
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "update test_templates set definition=?, modified_by=?, modified_date=? "
            "where id=? and code=? and version=? and status=? and definition=?",
            (json.dumps(definition), ACTOR, now, template_id, CODE, VERSION, "Active", raw_definition),
        )
        if cur.rowcount != 1:
            raise RuntimeError("Template changed during update")

        identity = con.execute(
            "select id, code, archetype, version, status, test_id from test_templates where id=?",
            (template_id,),
        ).fetchone()
        expected_identity = (template_id, code, archetype, version, status, test_id)
        if identity != expected_identity:
            raise RuntimeError(f"Template identity changed: {expected_identity} -> {identity}")

        con.commit()
        print(f"backup={backup.name}")
        print(f"template={CODE} v{VERSION} id={template_id}; table_footer_rows={len(TABLE_FOOTER_ROWS)}")
        print(f"validated_in_progress_worksheets={len(worksheets)}")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
