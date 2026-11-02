"""One-off: fit the "Drug release profile" Y-axis to the data (TPL-A6D-0002).

Y: from 0 in steps of 50, whole-number labels, top = next 50 above the highest
plotted value (no fixed 400 cap, so the line fills the frame). Plot height 460 px.
UI-only. Writes ONLY the `definition` column. Take a lims.db backup before
running without --validate-only.
"""
import argparse
import copy
import json
import sqlite3

from src.domain.services.calculation.template_schema import TemplateDefinition

DB = r"d:\RD-instance\GIT\backend-v2\lims.db"
CODE = "TPL-A6D-0002"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    db = sqlite3.connect(DB)
    tid, status, raw = db.execute(
        "select id, status, definition from test_templates where code=?", (CODE,)
    ).fetchone()
    new = copy.deepcopy(json.loads(raw))
    chart = next(g for g in new["groups"] if g["key"] == "release_chart")["chart"]
    chart["yAxis"] = {"min": 0, "step": 50, "digits": 0}
    chart["height"] = 460
    TemplateDefinition.parse(new)
    print("yAxis:", chart["yAxis"], "height:", chart["height"])
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
