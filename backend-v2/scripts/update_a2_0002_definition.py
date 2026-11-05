"""Synchronise TPL-A2-0002's tabular Standard Details layout in the catalogue.

The additive template seeder skips existing template codes, so this script copies
the version-controlled Lyso mg/mL definition (``a2_lyso_content.py``) to the
existing Active v1 row in ``lims.db`` without changing its identity, version,
status, result unit, or Test Master relationship.

The revised definition converts the ``standard`` ("Standard Details") group from
a ``singleton`` to a one-row ``table`` (``rows: {min:1, max:10, default:1}``) so
the worksheet gains add-row / delete-row controls. Every ``standard.<field>``
reference in the sample-result formulas keeps resolving against the first row
(the engine collapses a bare multi-row reference to row 0 at scalar coercion),
so all calculated values and acceptance criteria are preserved.

This is the module authoritative / DB re-seeded path: the module is the source of
truth and this writes it into the existing row in place. It does NOT bump the
version — the row stays v1 Active, matching the established in-place sync
convention (see ``update_a2_0006_definition.py``).

Run from ``backend-v2`` only after creating a database backup:
    python -m scripts.update_a2_0002_definition [db_path]

``db_path`` defaults to ``lims.db`` in the current directory. Pass the absolute
authoritative path when running from the worktree (whose converted module is the
source of truth) against the main-repo catalogue.
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone

from scripts.template_definitions.a2_lyso_content import LYSO

DB = "lims.db"
CODE = "TPL-A2-0002"
EXPECTED_NAME = "Content of Lyso PC / Lyso PG (mg/mL)"
ACTOR = "a2-0002-standard-details-tabular"


def _standard_is_tabular(definition: dict) -> bool:
    """Confirm the source/stored definition carries a tabular Standard Details."""
    groups = definition.get("groups", [])
    standard = next((g for g in groups if g.get("key") == "standard"), None)
    if standard is None:
        return False
    return (
        standard.get("kind") == "table"
        and standard.get("rows") == {"min": 1, "max": 10, "default": 1}
        #  Fields are unchanged by the conversion — the 16 per-compound inputs.
        and len(standard.get("fields", [])) == 16
    )


def main() -> int:
    """Update only the existing template definition and verify the result."""
    db_path = sys.argv[1] if len(sys.argv) > 1 else DB
    target_definition = LYSO.definition
    if not _standard_is_tabular(target_definition):
        print("ERROR: source definition does not carry a tabular Standard Details group")
        return 1

    definition_json = json.dumps(target_definition, ensure_ascii=False, separators=(",", ":"))
    con = sqlite3.connect(db_path)
    try:
        row = con.execute(
            "select id, code, name, archetype, version, status, test_id, result_unit, definition "
            "from test_templates where code=?",
            (CODE,),
        ).fetchone()
        if row is None:
            print(f"ERROR: {CODE} not found in {db_path}")
            return 1

        identity = row[:7]
        expected_identity = (
            identity[0],
            CODE,
            EXPECTED_NAME,
            "A2",
            1,
            "Active",
            identity[6],
        )
        if identity != expected_identity:
            print(f"ERROR: unexpected target identity: {identity!r}")
            return 1

        try:
            current_definition = json.loads(row[8])
        except json.JSONDecodeError as exc:
            print(f"ERROR: {CODE} has invalid stored JSON: {exc}")
            return 1

        if current_definition == target_definition:
            print(f"{CODE} is already synchronised; no database write performed")
            return 0

        now = datetime.now(timezone.utc).isoformat()
        cur = con.execute(
            "update test_templates set definition=?, modified_by=?, modified_date=? where code=?",
            (definition_json, ACTOR, now, CODE),
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
        if after[7] != row[7]:
            print(f"ERROR: result unit changed: before={row[7]!r}, after={after[7]!r}")
            return 1

        stored_definition = json.loads(after[8])
        if stored_definition != target_definition:
            print("ERROR: stored definition does not match the source definition")
            return 1
        if not _standard_is_tabular(stored_definition):
            print("ERROR: stored definition does not carry a tabular Standard Details group")
            return 1

        print(
            f"{CODE} updated; identity preserved "
            f"(id={identity[0]}, version={identity[4]}, status={identity[5]})"
        )
        print("Layout verified: Standard Details is now a table group (rows 1..10, default 1).")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
