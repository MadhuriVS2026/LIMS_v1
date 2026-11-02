"""Synchronise TPL-A2-0006's blank-interference layout in the local catalogue.

The additive template seeder skips existing template codes. This script therefore
copies the version-controlled sodium-chloride definition to the existing Active
v1 row in ``lims.db`` without changing its identity, version, status, result unit,
or Test Master relationship.

The revised definition removes the ``% Interference / Sodium`` calculated column
from the Blank Area table. It renders the same calculated value immediately below
the table as ``% Interference`` → ``Sodium (%)`` instead.

Run from ``backend-v2`` only after creating a database backup:
    python -m scripts.update_a2_0006_definition
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone

from scripts.template_definitions.a2_sodium_chloride_ic_mgvial import (
    SODIUM_CHLORIDE_IC,
)

DB = "lims.db"
CODE = "TPL-A2-0006"
EXPECTED_NAME = "Sodium_chloride_content by IC_ mgvial_Ampho"
ACTOR = "a2-0006-blank-interference-layout"


def _layout_is_expected(definition: dict) -> bool:
    """Confirm the source and stored definition use the requested layout."""
    groups = definition.get("groups", [])
    positions = {group.get("key"): index for index, group in enumerate(groups)}
    blank = next((group for group in groups if group.get("key") == "blank_areas"), None)
    interference = next(
        (group for group in groups if group.get("key") == "blank_interference"), None
    )
    if blank is None or interference is None:
        return False

    blank_fields = blank.get("fields", [])
    if [field.get("key") for field in blank_fields] != ["area"]:
        return False
    if positions["blank_interference"] != positions["blank_areas"] + 1:
        return False

    fields = interference.get("fields", [])
    return (
        interference.get("kind") == "singleton"
        and interference.get("label") == "% Interference"
        and len(fields) == 1
        and fields[0].get("key") == "sodium"
        and fields[0].get("kind") == "calculated"
        and fields[0].get("label") == "Sodium"
        and fields[0].get("unit") == "%"
        and fields[0].get("expression") == "stats.blank_interference"
    )


def main() -> int:
    """Update only the existing template definition and verify the result."""
    target_definition = SODIUM_CHLORIDE_IC.definition
    if not _layout_is_expected(target_definition):
        print("ERROR: source definition does not contain the requested below-table layout")
        return 1

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
        if not _layout_is_expected(stored_definition):
            print("ERROR: stored definition does not contain the requested below-table layout")
            return 1

        print(
            f"{CODE} updated; identity preserved "
            f"(id={identity[0]}, version={identity[4]}, status={identity[5]})"
        )
        print("Layout verified: % Interference / Sodium (%) appears below Blank Area — Sodium.")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
