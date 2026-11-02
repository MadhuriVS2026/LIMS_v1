"""Synchronise TPL-A10-0002's requested pycnometer layout to the local catalogue.

The additive template seeder skips existing codes. This script copies the
version-controlled definition to the existing Active v1 template without
changing its identity, version, status, result unit, or Test Master relationship.

Run from ``backend-v2`` after taking a database backup:
    python -m scripts.update_a10_0002_definition
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone

from scripts.template_definitions.a9_a10_a13_classical import A10_WPM

DB = "lims.db"
CODE = "TPL-A10-0002"
EXPECTED_NAME = "Weight per mL (pycnometer)"
ACTOR = "a10-0002-pycnometer-layout"


def _layout_is_expected(definition: dict) -> bool:
    """Confirm the source and stored definition contain the requested layout."""
    determinations = next(
        (group for group in definition.get("groups", []) if group.get("key") == "determinations"),
        None,
    )
    if determinations is None:
        return False

    expected_fields = [
        ("batch_no", "input", "Batch No"),
        ("info", "input", "Info"),
        ("empty_weight", "input", "wt of pycnometer, Empty (W)"),
    ]
    actual_fields = determinations.get("fields", [])
    return (
        determinations.get("kind") == "table"
        and determinations.get("label") == "Weight determination using Pycnometer"
        and [
            (field.get("key"), field.get("kind"), field.get("label"))
            for field in actual_fields[: len(expected_fields)]
        ]
        == expected_fields
        and actual_fields[1].get("multiline") is True
        and sum(field.get("key") == "empty_weight" for field in actual_fields) == 1
        and all(field.get("key") != "prep_ref" for field in actual_fields)
        and _gross_section_is_expected(definition)
    )


def _gross_section_is_expected(definition: dict) -> bool:
    """Confirm the second pycnometer section and its Average footer are present."""
    gross = next(
        (g for g in definition.get("groups", []) if g.get("key") == "gross_content"),
        None,
    )
    if gross is None or gross.get("label") != "Weight determination using Pycnometer 2":
        return False
    keys = [f.get("key") for f in gross.get("fields", [])]
    expected = [
        "batch_no",
        "info",
        "filled_weight",
        "empty_weight",
        "net_weight",
        "gross_content_ml",
    ]
    if keys != expected:
        return False
    footer_rows = gross.get("tableFooterRows", [])
    if not footer_rows or footer_rows[0].get("label") != "Average":
        return False
    value = footer_rows[0].get("values", {}).get("gross_content_ml", {})
    return value.get("ref") == "gross_stats.mean_gross_content"


def main() -> int:
    """Update only the existing template definition and verify the result."""
    target_definition = A10_WPM.definition
    if not _layout_is_expected(target_definition):
        print("ERROR: source definition does not contain the requested pycnometer layout")
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
        expected_identity = (identity[0], CODE, EXPECTED_NAME, "A10", 1, "Active", identity[6])
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
            print("ERROR: stored definition does not contain the requested pycnometer layout")
            return 1

        print(
            f"{CODE} updated; identity preserved "
            f"(id={identity[0]}, version={identity[4]}, status={identity[5]})"
        )
        print(
            "Layout verified: Info is an auto-growing wrapped text column; "
            "Batch No leads a single wt of pycnometer, Empty (W) (g) column."
        )
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
