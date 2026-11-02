"""One-off: remove the "µV·s" unit from every field of TPL-A6D-0002.

Units are display-only (column header suffix); no formula reads them. Writes
ONLY the `definition` column. Take a lims.db backup before running without
--validate-only.
"""
import argparse
import copy
import json
import sqlite3

from src.domain.services.calculation.template_schema import TemplateDefinition

DB = r"d:\RD-instance\GIT\backend-v2\lims.db"
CODE = "TPL-A6D-0002"
UNIT = "µV·s"


def mutate(definition: dict) -> tuple[dict, list[str]]:
    new = copy.deepcopy(definition)
    removed = []
    for g in new["groups"]:
        for f in g.get("fields", []):
            if f.get("unit") == UNIT:
                del f["unit"]
                removed.append(f"{g['key']}.{f['key']}")
    for f in new.get("context", []):
        if f.get("unit") == UNIT:
            del f["unit"]
            removed.append(f["key"])
    return new, removed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    db = sqlite3.connect(DB)
    tid, status, raw = db.execute(
        "select id, status, definition from test_templates where code=?", (CODE,)
    ).fetchone()
    new, removed = mutate(json.loads(raw))
    assert removed, "no µV·s units found"
    assert UNIT not in json.dumps(new, ensure_ascii=False)
    TemplateDefinition.parse(new)
    print(f"{len(removed)} fields lose the unit:", removed)
    if args.validate_only:
        print("--validate-only: no DB write")
        return
    db.execute("update test_templates set definition=? where id=?", (json.dumps(new), tid))
    db.commit()
    assert json.loads(db.execute("select definition from test_templates where id=?", (tid,)).fetchone()[0]) == new
    assert db.execute("select status from test_templates where id=?", (tid,)).fetchone()[0] == status
    print("written and re-read byte-equal; status:", status)


if __name__ == "__main__":
    main()
