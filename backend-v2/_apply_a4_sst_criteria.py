"""Add the requested SST Criteria section to active TPL-A4-0003 v1.

The update preserves the active template identity and moves legacy SST result
values into the new section for its in-progress worksheets. A timestamped SQLite
backup is made before any data is changed.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

DB = Path("lims.db")
CODE = "TPL-A4-0003"
VERSION = 1
ACTOR = "kiro-a4sstcriteria"

SEED_ROWS = (
    {
        "criterion": (
            "Resolution Between GS-833150 & GS-833248 "
            "(Des Bromo & LCV Keto) in SST Solition"
        ),
        "limit": "≥ 1.0",
        "legacy_key": "resolution_desbromo_keto",
    },
    {
        "criterion": (
            "Resolution Between LENA-2078 & LENA-3243 "
            "(Amine Imp. & LKH IV (i)) in SST Solition"
        ),
        "limit": "≥ 1.0",
        "legacy_key": "resolution_amine_lkh",
    },
    {
        "criterion": "Tailing Factor for Lenacapavir-2 Peak from STD / Inj-5",
        "limit": "0.8 - 1.5",
        "legacy_key": "tailing_lena2",
    },
    {
        "criterion": "Retention time of Lenacapavir-2 Peak from Sample",
        "limit": "NA",
        "legacy_key": "rt_lena2_sample",
    },
)


def sst_criteria_group() -> dict[str, Any]:
    return {
        "key": "sst_criteria",
        "kind": "table",
        "label": "SST Criteria",
        "showRowNumbers": False,
        "rows": {
            "min": 4,
            "max": 4,
            "default": 4,
            "seed": [
                {"criterion": row["criterion"], "limit": row["limit"]}
                for row in SEED_ROWS
            ],
        },
        "fields": [
            {
                "key": "criterion",
                "kind": "input",
                "type": "text",
                "label": "SST Critereia",
                "width": "78%",
            },
            {
                "key": "result",
                "kind": "input",
                "type": "text",
                "label": "Result",
                "width": "11%",
            },
            {
                "key": "limit",
                "kind": "input",
                "type": "text",
                "label": "Limit",
                "width": "11%",
            },
        ],
    }


def formatted_result(value: Any) -> str | None:
    """Preserve blank values; display numeric legacy results to three decimals."""
    if value is None or value == "":
        return None
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return str(value)


def migrate_group_values(raw: str) -> tuple[dict[str, Any], bool]:
    values = json.loads(raw or "{}")
    sst_rows = values.get("sst") or [{}]
    sst = sst_rows[0] if isinstance(sst_rows[0], dict) else {}
    changed = False

    # The active template defines this as a numeric input. One legacy worksheet
    # stores it as text, which prevents its existing Sensitivity calculation from
    # evaluating after the template definition is parsed.
    dilution_factor = sst.get("dilution_factor")
    if isinstance(dilution_factor, str) and dilution_factor.strip():
        try:
            sst["dilution_factor"] = float(dilution_factor)
            changed = True
        except ValueError:
            pass

    if "sst_criteria" in values:
        return values, changed

    values["sst_criteria"] = [
        {
            "criterion": row["criterion"],
            "result": formatted_result(sst.get(row["legacy_key"])),
            "limit": row["limit"],
        }
        for row in SEED_ROWS
    ]
    return values, True


def backup_database() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"lims.db.bak-a4sstcriteria-{stamp}")
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
        groups = definition.get("groups") or []
        sst_index = next(
            (index for index, group in enumerate(groups) if group.get("key") == "sst"),
            None,
        )
        if sst_index is None:
            raise RuntimeError("The Sensitivity group is missing from the active template")

        requested_group = sst_criteria_group()
        existing = [group for group in groups if group.get("key") == "sst_criteria"]
        definition_changed = False
        if not existing:
            groups.insert(sst_index + 1, requested_group)
            definition["groups"] = groups
            definition_changed = True
        elif existing != [requested_group]:
            raise RuntimeError("An unexpected SST Criteria section already exists")

        parsed = TemplateDefinition.parse(definition)
        evaluator = WorksheetEvaluator(parsed)

        worksheets = con.execute(
            "select id, group_values from test_worksheets "
            "where template_id=? and template_version=? and status=? order by id",
            (template_id, VERSION, "InProgress"),
        ).fetchall()
        migrated_worksheets = 0
        for worksheet_id, raw_values in worksheets:
            values, changed = migrate_group_values(raw_values)
            evaluator.evaluate({}, values)
            if changed:
                cur = con.execute(
                    "update test_worksheets set group_values=?, modified_by=?, modified_date=? "
                    "where id=? and status=?",
                    (json.dumps(values), ACTOR, now, worksheet_id, "InProgress"),
                )
                if cur.rowcount != 1:
                    raise RuntimeError(f"Worksheet {worksheet_id} changed during migration")
                migrated_worksheets += 1

        if definition_changed:
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
        print(f"template={CODE} v{VERSION} id={template_id}; definition_changed={definition_changed}")
        print(f"migrated_in_progress_worksheets={migrated_worksheets}")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
