"""Sync the stored TPL-A6B-0001 definition in lims.db from the source module.

The seeder skips codes that already exist, so a rebuilt A6b definition never
reaches the DB through reseeding. This script is the documented sync mechanism:
it serialises `A6B.definition` from scripts.template_definitions.a6_dissolution
and writes it over the stored `definition` JSON of the existing TPL-A6B-0001 row,
touching nothing else (code, archetype, test_id, status, version, approved_by all
unchanged). Idempotent — running it twice is a no-op in content.
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone

from scripts.template_definitions.a6_dissolution import A6B

DB = "lims.db"
CODE = "TPL-A6B-0001"


def main() -> int:
    definition_json = json.dumps(A6B.definition)
    now = datetime.now(timezone.utc).isoformat()

    con = sqlite3.connect(DB)
    try:
        before = con.execute(
            "select id, code, archetype, version, status, test_id from test_templates"
            " where code=?",
            (CODE,),
        ).fetchone()
        if before is None:
            print(f"ERROR: {CODE} not found in {DB}")
            return 1

        cur = con.execute(
            "update test_templates set definition=?, modified_by=?, modified_date=?"
            " where code=?",
            (definition_json, "a6b-rebuild", now, CODE),
        )
        con.commit()
        print(f"{cur.rowcount} row updated")

        after = con.execute(
            "select id, code, archetype, version, status, test_id from test_templates"
            " where code=?",
            (CODE,),
        ).fetchone()
        assert cur.rowcount == 1, "expected exactly one row updated"
        assert before == after, (
            f"identity columns changed: {before} -> {after}"
        )
        print(f"identity preserved: id={after[0]} archetype={after[2]} "
              f"version={after[3]} status={after[4]} test_id={after[5]}")
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
