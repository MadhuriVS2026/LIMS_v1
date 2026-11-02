"""Render active TPL-A4-0003 v1 Standard Injections as a one-row table.

The existing calculated fields and expressions remain unchanged. The update only
changes the group's presentation kind from singleton to a fixed one-row table,
without a row-number column, so the STD-1..6, Mean, SD, and %RSD values display
as spreadsheet-style columns.
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
ACTOR = "kiro-a4stdinjtable"


def backup_database() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"lims.db.bak-a4stdinjtable-{stamp}")
    with sqlite3.connect(DB) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    return backup


def main() -> int:
    if not DB.is_file():
        print(f"ERROR: {DB} does not exist")
        return 1

    backup = backup_database()
    now = datetime.now().isoformat(timespec="seconds")

    con = sqlite3.connect(DB, timeout=30)
    try:
        con.execute("BEGIN IMMEDIATE")
        template = con.execute(
            "select id, code, archetype, version, status, test_id, definition "
            "from test_templates where code=? and version=? and status=?",
            (CODE, VERSION, "Active"),
        ).fetchone()
        if template is None:
            raise RuntimeError(f"Active {CODE} v{VERSION} was not found")

        template_id, code, archetype, version, status, test_id, raw_definition = template
        definition = json.loads(raw_definition)
        group = next(
            (item for item in definition.get("groups", []) if item.get("key") == "std_injections"),
            None,
        )
        if group is None:
            raise RuntimeError("Standard Injections group is missing")
        if group.get("kind") != "singleton":
            raise RuntimeError("Standard Injections is not in its expected singleton form")

        group["kind"] = "table"
        group["showRowNumbers"] = False
        group["rows"] = {"min": 1, "max": 1, "default": 1}

        parsed = TemplateDefinition.parse(definition)
        evaluator = WorksheetEvaluator(parsed)
        worksheets = con.execute(
            "select id, group_values from test_worksheets "
            "where template_id=? and template_version=? and status=? order by id",
            (template_id, VERSION, "InProgress"),
        ).fetchall()
        for worksheet_id, raw_values in worksheets:
            try:
                evaluator.evaluate({}, json.loads(raw_values or "{}"))
            except Exception as exc:
                raise RuntimeError(f"Worksheet {worksheet_id} failed after conversion: {exc}") from exc

        cur = con.execute(
            "update test_templates set definition=?, modified_by=?, modified_date=? "
            "where id=? and code=? and version=? and status=?",
            (json.dumps(definition), ACTOR, now, template_id, CODE, VERSION, "Active"),
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
        print(f"template={CODE} v{VERSION} id={template_id}; group=std_injections; kind=table")
        print(f"validated_in_progress_worksheets={len(worksheets)}")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
