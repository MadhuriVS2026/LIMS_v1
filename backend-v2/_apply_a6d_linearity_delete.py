"""One-off: allow deleting rows in "Standard Tapinarof for Linearity" (TPL-A6D-0002).

The table opened at its minimum (min 9 = 9 seeded rows), so the form disabled
every delete button. min is lowered to 2, the fewest points a calibration curve
can be fitted through. The table still opens with the same 9 seeded rows.

Writes ONLY the `definition` column. Take a lims.db backup before running
without --validate-only.
"""
import argparse
import copy
import json
import sqlite3

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

DB = r"d:\RD-instance\GIT\backend-v2\lims.db"
CODE = "TPL-A6D-0002"
AREAS = [200754, 974514, 2922207, 5786622, 7842177, 11507227]


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    lin = next(g for g in new["groups"] if g["key"] == "linearity")
    lin["rows"]["min"] = 2
    return new


def check(definition: dict) -> None:
    parsed = TemplateDefinition.parse(definition)
    rows = parsed.group("linearity").rows
    assert (rows.min, rows.default, rows.max, len(rows.seed)) == (2, 9, 15, 9), rows
    ev = WorksheetEvaluator(parsed)
    assert ev.evaluate({}, {}).has_blocking_failure is False

    seed = [dict(r) for r in next(g for g in definition["groups"] if g["key"] == "linearity")["rows"]["seed"]]
    for r, a in zip(seed, AREAS):
        r["area"] = a
    full = ev.evaluate({}, {"linearity": seed}).values
    assert full["curve.curve_slope"] == 53797.61 and full["curve.curve_intercept"] == 28844.9

    #  Delete the three QC rows and one standard: the curve refits on the 5 left.
    trimmed = seed[:2] + seed[3:6]
    res = ev.evaluate({}, {"linearity": trimmed}).values
    print("after deleting 4 rows -> slope", res["curve.curve_slope"],
          "intercept", res["curve.curve_intercept"], "correlation", res["curve.correlation"])
    assert res["curve.curve_slope"] not in (None, "") and res["curve.curve_slope"] != 53797.61


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    db = sqlite3.connect(DB)
    tid, status, raw = db.execute(
        "select id, status, definition from test_templates where code=?", (CODE,)
    ).fetchone()
    new = mutate(json.loads(raw))
    check(new)
    if args.validate_only:
        print("--validate-only: no DB write")
        return
    db.execute("update test_templates set definition=? where id=?", (json.dumps(new), tid))
    db.commit()
    back = json.loads(db.execute("select definition from test_templates where id=?", (tid,)).fetchone()[0])
    assert back == new
    assert db.execute("select status from test_templates where id=?", (tid,)).fetchone()[0] == status
    print("written and re-read byte-equal; status:", status)


if __name__ == "__main__":
    main()
