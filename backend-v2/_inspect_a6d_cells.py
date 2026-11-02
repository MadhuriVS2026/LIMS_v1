"""Read-only: compare the A6D-0002 'cells' data in the live DB vs a backup DB."""
import json
import sqlite3
import sys

CODE = "TPL-A6D-0002"


def dump(path: str) -> None:
    db = sqlite3.connect(path)
    row = db.execute(
        "select id, status, definition from test_templates where code=?", (CODE,)
    ).fetchone()
    if not row:
        print(f"[{path}] template {CODE} NOT FOUND")
        return
    tid, status, raw = row
    d = json.loads(raw)
    cells = next((g for g in d["groups"] if g["key"] == "cells"), None)
    print(f"=== {path}")
    print(f"  template id={tid} status={status}")
    if cells is None:
        print("  cells group: ABSENT from definition")
    else:
        print(f"  cells kind={cells.get('kind')} label={cells.get('label')!r}")
        print(f"  cells rows={json.dumps(cells.get('rows', {}))}")
        print(f"  cells fields={[f['key'] for f in cells.get('fields', [])]}")
    for wid, gv in db.execute(
        "select id, group_values from test_worksheets where template_id=?", (tid,)
    ):
        g = json.loads(gv) if gv else {}
        print(f"  worksheet {wid}: cells={json.dumps(g.get('cells'))}")
    db.close()


if __name__ == "__main__":
    for p in sys.argv[1:]:
        dump(p)
        print()
