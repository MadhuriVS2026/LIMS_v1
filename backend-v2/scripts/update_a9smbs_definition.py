"""Sync the stored TPL-A9-0002 definition in lims.db from the source module.

The seeder skips codes that already exist, so edits to the Sodium Metabisulfite
definition (per-row Normality column; % Mean moved out of the table into a
singleton Result group) never reach the DB through reseeding. This script
serialises `A9_SMBS.definition` from
scripts.template_definitions.a9_sodium_metabisulfite and writes it over the
stored `definition` JSON of the existing TPL-A9-0002 row, touching nothing else
(code, archetype, test_id, status, version, approved_by all unchanged).
Idempotent — running it twice is a no-op in content.
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone

from scripts.template_definitions.a9_sodium_metabisulfite import A9_SMBS

DB = "lims.db"
CODE = "TPL-A9-0002"


def main() -> int:
    definition_json = json.dumps(A9_SMBS.definition)
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
            (definition_json, "a9smbs-edit", now, CODE),
        )
        con.commit()
        print(f"{cur.rowcount} row updated")

        after = con.execute(
            "select id, code, archetype, version, status, test_id from test_templates"
            " where code=?",
            (CODE,),
        ).fetchone()
        assert cur.rowcount == 1, "expected exactly one row updated"
        assert before == after, f"identity columns changed: {before} -> {after}"
        print(
            f"identity preserved: id={after[0]} archetype={after[2]} "
            f"version={after[3]} status={after[4]} test_id={after[5]}"
        )
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
