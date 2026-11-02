"""Make the Lenacapavir Sensitivity STD/Inj-1 area a manual entry.

The calculated Sensitivity result remains unchanged. Only the source of its
standard peak area changes from the first Standard Injections row to an analyst
entered chromatographic-area value in the System Suitability / Sensitivity form.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

DB = Path("lims.db")
CODE = "TPL-A4-0003"
VERSION = 1
ACTOR = "kiro-a4manualsststdarea"
FIELD_KEY = "area_lena2_std"


def proposed_definition(raw_definition: str) -> dict:
    definition = json.loads(raw_definition)
    sst = next((group for group in definition.get("groups", []) if group.get("key") == "sst"), None)
    if sst is None:
        raise RuntimeError("System Suitability / Sensitivity group is missing")

    index = next(
        (position for position, field in enumerate(sst.get("fields", [])) if field.get("key") == FIELD_KEY),
        None,
    )
    if index is None:
        raise RuntimeError("Sensitivity STD/Inj-1 area field is missing")
    current = sst["fields"][index]
    if current.get("kind") != "calculated":
        raise RuntimeError("Sensitivity STD/Inj-1 area is not in its expected calculated form")

    sst["fields"][index] = {
        "key": FIELD_KEY,
        "kind": "area",
        "label": "Area of Lenacapavir-2 Peak from STD / Inj-1",
    }
    return definition


def validate_manual_entry(evaluator: WorksheetEvaluator) -> None:
    result = evaluator.evaluate(
        {},
        {
            "sst": [
                {
                    "area_lena2_sensitivity": 4388,
                    "area_lena2_std": 9298867,
                    "dilution_factor": 2000,
                }
            ]
        },
    )
    if result.values["sst.result"] != 0.944:
        raise RuntimeError(f"Manual Sensitivity calculation mismatch: {result.values['sst.result']}")


def backup_database() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"lims.db.bak-a4manualsststdarea-{stamp}")
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
        validate_manual_entry(evaluator)

        worksheets = con.execute(
            "select id, context_values, group_values from test_worksheets "
            "where template_id=? and template_version=? and status=? order by id",
            (template_id, VERSION, "InProgress"),
        ).fetchall()
        for worksheet_id, raw_context, raw_values in worksheets:
            try:
                evaluator.evaluate(json.loads(raw_context or "{}"), json.loads(raw_values or "{}"))
            except Exception as exc:
                raise RuntimeError(f"Worksheet {worksheet_id} failed after manual-area update: {exc}") from exc

        if validate_only:
            print(f"valid={CODE} v{VERSION}; manual_field={FIELD_KEY}")
            print("manual_sensitivity_example=4388 / 9298867 * 2000 = 0.944")
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
        print(f"template={CODE} v{VERSION} id={template_id}; manual_field={FIELD_KEY}")
        print(f"validated_in_progress_worksheets={len(worksheets)}")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
