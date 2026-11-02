"""One-off: add "Cumulative drug release (µg)" below the correction-factor table (TPL-A6D-0002).

Read-only view over the existing `timepoints.cumulative_n`:
  cumulative_n = amount_n + carry_n, where carry_n = sum of all earlier amounts x
  sample withdrawn / cell volume (= the running total of the correction factors).
This is the value the Release Rate flux is fitted on. No new calculation.

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
TITLE = "Cumulative drug release (µg)"
BAND = "Cumulative Drug release (µg) = Amount calculated+ correction factor"
CELLS = range(1, 11)

SHEET = [
    (40, 1069016, 688177, 1058932, 1274902, 749441, 1082016),
    (80, 1501219, 1072893, 1466796, 1754152, 1042199, 1498375),
    (120, 1772227, 1366683, 1706687, 2156378, 1245758, 1773041),
    (160, 1883830, 1564759, 1850820, 2338036, 1300307, 1881978),
    (200, 1962798, 1749653, 1935150, 2371001, 1397948, 1959299),
    (240, 2015676, 1839654, 1991104, 2521117, 1402166, 2014489),
]
WANT = [
    (135.3443, 85.7905, 134.0322, 162.1336, 93.7620, 137.0358),
    (210.9162, 148.1045, 206.2498, 247.6543, 145.2495, 210.7878),
    (273.5478, 205.7386, 264.1926, 332.0611, 190.5724, 273.8425),
    (320.4756, 256.3797, 314.1349, 395.2450, 220.2904, 320.4386),
    (365.2315, 308.9875, 358.9749, 442.4580, 256.6294, 364.9457),
    (408.0606, 352.6849, 401.6902, 505.5271, 282.6274, 408.0106),
]


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    keys = [g["key"] for g in new["groups"]]
    assert "timepoint_cumulative" not in keys, "already applied"
    tp_keys = {f["key"] for f in next(g for g in new["groups"] if g["key"] == "timepoints")["fields"]}
    assert all(f"cumulative_{n}" in tp_keys for n in CELLS)

    columns = [{"key": "time_min", "label": "Time in Min", "digits": 1}] + [
        {"key": f"cumulative_{n}", "label": f"Cell-{n}", "digits": 4,
         "showIf": f"cells.cell_no[{n - 1}]", "band": BAND}
        for n in CELLS
    ]
    group = {
        "key": "timepoint_cumulative",
        "kind": "singleton",
        "label": TITLE,
        "fields": [
            {"key": "timepoint_count", "kind": "calculated", "label": "Timepoints",
             "expression": "count(timepoints.time_min)", "hidden": True},
        ],
        "view": {"sourceGroup": "timepoints", "columns": columns},
    }
    at = keys.index("timepoint_cf") + 1
    new["groups"][at:at] = [group]
    return new


def check(definition: dict) -> None:
    parsed = TemplateDefinition.parse(definition)
    ev = WorksheetEvaluator(parsed)
    assert ev.evaluate({}, {}).has_blocking_failure is False
    assert parsed.result_ref == "flux.mean_flux"

    lin = [dict(r) for r in next(g for g in definition["groups"] if g["key"] == "linearity")["rows"]["seed"]]
    for r, a in zip(lin, [200754, 974514, 2922207, 5786622, 7842177, 11507227]):
        r["area"] = a
    cells = [{"cell_no": f"Cell {n}", "weight_mg": 250} for n in range(1, 7)]
    tp = [{"time_min": s[0], **{f"area_{n}": s[n] for n in range(1, 7)}} for s in SHEET]
    res = ev.evaluate({}, {"linearity": lin, "cells": cells, "timepoints": tp})

    bad = [(SHEET[i][0], n, round(res.row_value("timepoints", i, f"cumulative_{n}"), 4), WANT[i][n - 1])
           for i in range(6) for n in range(1, 7)
           if round(res.row_value("timepoints", i, f"cumulative_{n}"), 4) != WANT[i][n - 1]]
    assert not bad, bad
    print("all 36 cumulative values match the sheet to 4 decimals; 120 min Cell-1 =",
          f"{res.row_value('timepoints', 2, 'cumulative_1'):.4f}")
    #  cumulative = amount + running total of correction factors
    for i in range(6):
        cf_total = sum(res.row_value("timepoints", j, "cf_1") for j in range(i + 1))
        assert abs(res.row_value("timepoints", i, "amount_1") + cf_total
                   - res.row_value("timepoints", i, "cumulative_1")) < 1e-9
    print("cumulative = amount + sum of correction factors to date: OK")


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
    print("order:", [g["key"] for g in new["groups"]])
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
