"""Synchronise TPL-A11-0003's definition to the local SQLite catalogue.

The additive seeder deliberately skips templates that already exist. This script
therefore writes the definition and result unit from the version-controlled
source to the existing active v1 template without changing its identity, workflow
status, or Test Master relationship.

Run from ``backend-v2`` after taking a database backup:
    python -m scripts.update_a11_0003_definition
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone

from scripts.template_definitions.a11_microbial_bioassay import A11_AMPHO_API

DB = "lims.db"
CODE = "TPL-A11-0003"
EXPECTED_NAME = "Assay-Microbial-Ampho-API"
ACTOR = "a11-ampho-api-stock-only"


def main() -> int:
    """Synchronise the target definition and its reportable result unit."""
    target_definition = A11_AMPHO_API.definition
    target_result_unit = A11_AMPHO_API.result_unit
    definition_json = json.dumps(target_definition, ensure_ascii=False, separators=(",", ":"))

    con = sqlite3.connect(DB)
    try:
        row = con.execute(
            "select id, code, name, archetype, version, status, test_id, result_unit, definition "
            "from test_templates where code=?",
            (CODE,),
        ).fetchone()
        if row is None:
            print(f"ERROR: {CODE} not found in {DB}")
            return 1

        identity = row[:7]
        expected_identity = (identity[0], CODE, EXPECTED_NAME, "A11", 1, "Active", identity[6])
        if identity != expected_identity:
            print(f"ERROR: unexpected target identity: {identity!r}")
            return 1

        current_result_unit = row[7]
        try:
            current_definition = json.loads(row[8])
        except json.JSONDecodeError as exc:
            print(f"ERROR: {CODE} has invalid stored JSON: {exc}")
            return 1

        if current_definition == target_definition and current_result_unit == target_result_unit:
            print(f"{CODE} is already synchronised; no database write performed")
            return 0

        now = datetime.now(timezone.utc).isoformat()
        cur = con.execute(
            "update test_templates set definition=?, result_unit=?, modified_by=?, modified_date=? "
            "where code=?",
            (definition_json, target_result_unit, ACTOR, now, CODE),
        )
        con.commit()
        if cur.rowcount != 1:
            print(f"ERROR: expected one update, received {cur.rowcount}")
            return 1

        after = con.execute(
            "select id, code, name, archetype, version, status, test_id, result_unit, definition "
            "from test_templates where code=?",
            (CODE,),
        ).fetchone()
        if after is None or after[:7] != identity:
            print(f"ERROR: target identity changed: before={identity!r}, after={after!r}")
            return 1
        if after[7] != target_result_unit:
            print(f"ERROR: stored result unit does not match {target_result_unit!r}")
            return 1
        if json.loads(after[8]) != target_definition:
            print("ERROR: stored definition does not match the source definition")
            return 1

        print(
            f"{CODE} updated; identity preserved "
            f"(id={identity[0]}, version={identity[4]}, result_unit={target_result_unit})"
        )
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
