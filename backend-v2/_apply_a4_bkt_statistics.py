"""Add pooled Mean, SD, and %RSD to the active TPL-A4-0003 BKT block.

The existing BKT Mean and %RSD calculations are already pooled with the six
standard injections. This update preserves that basis, adds the matching pooled
SD calculation, and exposes all three statistics below the BKT table.
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
ACTOR = "kiro-a4bktstats"

BKT_FOOTER = [
    {"label": "Mean", "ref": "stats.mean_bkt", "rounding": {"mode": "round", "digits": 0}},
    {"label": "SD", "ref": "stats.sd_bkt", "rounding": {"mode": "round", "digits": 2}},
    {
        "label": "% RSD",
        "ref": "stats.rsd_bkt",
        "unit": "%",
        "rounding": {"mode": "round", "digits": 2},
    },
]

SD_BKT_FIELD = {
    "key": "sd_bkt",
    "kind": "calculated",
    "label": "BKT SD",
    "expression": "sd(pool(std_preps.area, bkt.area))",
    "rounding": {"mode": "round", "digits": 2},
}


def backup_database() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"lims.db.bak-a4bktstats-{stamp}")
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
        groups = {group.get("key"): group for group in definition.get("groups", [])}
        bkt = groups.get("bkt")
        stats = groups.get("stats")
        if bkt is None or stats is None:
            raise RuntimeError("BKT or Standard Statistics group is missing")
        if bkt.get("footer"):
            raise RuntimeError("BKT already has a footer")

        stat_fields = stats.get("fields", [])
        mean_index = next(
            (index for index, field in enumerate(stat_fields) if field.get("key") == "mean_bkt"),
            None,
        )
        if mean_index is None:
            raise RuntimeError("BKT Mean field is missing")
        if any(field.get("key") == "sd_bkt" for field in stat_fields):
            raise RuntimeError("BKT SD field already exists")

        stat_fields.insert(mean_index + 1, SD_BKT_FIELD)
        bkt["footer"] = BKT_FOOTER

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
                raise RuntimeError(f"Worksheet {worksheet_id} failed after update: {exc}") from exc

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
        print(f"template={CODE} v{VERSION} id={template_id}; BKT footer=Mean/SD/%RSD")
        print(f"validated_in_progress_worksheets={len(worksheets)}")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
