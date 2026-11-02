"""One-off: whole-number Y-axis labels on the "Drug release profile" graph (TPL-A6D-0002).

Y labels 0, 50, 100 ... 400 (no decimals), one per 50 step. UI-only.
Writes ONLY the `definition` column. Take a lims.db backup before running
without --validate-only.
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
    chart["yAxis"] = {"min": 0, "max": 400, "step": 50, "digits": 0}
    TemplateDefinition.parse(new)
    print("yAxis:", chart["yAxis"], "xAxis:", chart["xAxis"])
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
