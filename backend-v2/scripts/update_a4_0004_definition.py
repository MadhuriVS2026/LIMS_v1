"""Sync the stored TPL-A4-0004 definition in lims.db from the source module.

The seeder skips codes that already exist, so a rebuilt A4-0004 definition never
reaches the DB through reseeding, and the app approve/e-sign flow must NOT be
used to mutate an Active template. This script is the documented sync mechanism:
it serialises `A4_RRF_DIVISION.definition` from
scripts.template_definitions.a4_rs_against_standard_rrf_division and writes it
over the stored `definition` JSON of the existing TPL-A4-0004 row, touching
nothing else — id, code, archetype, version, status and test_id are all asserted
unchanged. Idempotent: running it twice is a no-op in content.

This revision replaced the "Known Impurities (against standard)" table with a
single "Calculation of unknown impurities against standard" table (one
`response` column per impurity, RRF applied as a division factor), and reduced
the summary to Single maximum unknown impurity + Total unknown impurities.
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone

from scripts.template_definitions.a4_rs_against_standard_rrf_division import (
    A4_RRF_DIVISION,
)

DB = "lims.db"
CODE = "TPL-A4-0004"


def main() -> int:
    definition_json = json.dumps(A4_RRF_DIVISION.definition)
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
            (definition_json, "a4-0004-unknowns", now, CODE),
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
