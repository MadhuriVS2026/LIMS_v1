"""One-off: Excel-style axes for the "Drug release profile" graph (TPL-A6D-0002).

Y: 0 to 400 in steps of 50, 3-decimal labels (0.000 ... 400.000).
X: 5.0 to 17.0 in steps of 2, 1-decimal labels.
Diamond markers. The frontend widens an axis past these limits if a run's
data falls outside them. UI-only; no calculation changes.

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


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    chart = next(g for g in new["groups"] if g["key"] == "release_chart")["chart"]
    chart["yAxis"] = {"min": 0, "max": 400, "step": 50, "digits": 3}
    chart["xAxis"] = {"min": 5, "max": 17, "step": 2, "digits": 1}
    chart["pointStyle"] = "rectRot"
    return new


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    db = sqlite3.connect(DB)
    tid, status, raw = db.execute(
        "select id, status, definition from test_templates where code=?", (CODE,)
    ).fetchone()
    new = mutate(json.loads(raw))
    TemplateDefinition.parse(new)
    print("chart:", json.dumps({k: new_v for k, new_v in next(
        g for g in new["groups"] if g["key"] == "release_chart")["chart"].items()
        if k in ("xAxis", "yAxis", "pointStyle")}))
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
