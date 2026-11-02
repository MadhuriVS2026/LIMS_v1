"""One-off: add "Sample-Timepoints-Concentration" below the Sampling-Timepoints table (TPL-A6D-0002).

A read-only table (UI `view` hint on a singleton) over the `timepoints` rows:
Time in Min | Concentration in µg: Cell-1 .. Cell-10.
Each value is the existing amount_n = (area - intercept) / slope x sample_vol /
sample_pip x receptor volume (uncorrected; no carry-over). Rows follow the
Sampling-Timepoints table; Cell-n columns follow Cell Loading (showIf).
No new calculation: the group carries one hidden helper (timepoint count) only
because the schema requires a non-empty field list.

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
TITLE = "Sample-Timepoints-Concentration"

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
    (191.5813, 135.8487, 187.1023, 224.4923, 131.8549, 191.2113),
    (226.8442, 174.0759, 218.3163, 276.8289, 158.3415, 226.9501),
    (241.3657, 199.8490, 237.0705, 300.4657, 165.4392, 241.1247),
    (251.6408, 223.9069, 248.0433, 304.7550, 178.1440, 251.1855),
    (258.5211, 235.6176, 255.3239, 324.2877, 178.6928, 258.3667),
]


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    keys = [g["key"] for g in new["groups"]]
    assert "timepoint_conc" not in keys, "already applied"
    tp_fields = {f["key"] for f in next(g for g in new["groups"] if g["key"] == "timepoints")["fields"]}
    n_cells = sum(1 for k in tp_fields if k.startswith("amount_"))
    assert n_cells == 10, n_cells

    columns = [{"key": "time_min", "label": "Time in Min", "digits": 1}]
    for n in range(1, n_cells + 1):
        assert f"amount_{n}" in tp_fields
        columns.append({"key": f"amount_{n}", "label": f"Cell-{n}", "digits": 4,
                        "showIf": f"cells.cell_no[{n - 1}]", "band": "Concentration in µg"})
    group = {
        "key": "timepoint_conc",
        "kind": "singleton",
        "label": TITLE,
        "fields": [
            {"key": "timepoint_count", "kind": "calculated", "label": "Timepoints",
             "expression": "count(timepoints.time_min)", "hidden": True},
        ],
        "view": {"sourceGroup": "timepoints", "columns": columns},
    }
    at = keys.index("timepoints") + 1
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

    view = next(g for g in definition["groups"] if g["key"] == "timepoint_conc")["view"]
    bad = []
    for i in range(6):
        for n in range(1, 7):
            col = view["columns"][n]
            shown = round(res.row_value(view["sourceGroup"], i, col["key"]), col["digits"])
            if shown != WANT[i][n - 1]:
                bad.append((SHEET[i][0], n, shown, WANT[i][n - 1]))
    assert not bad, bad
    print("all 36 concentrations match the sheet to 4 decimals; e.g. 40 min Cell-1 =",
          f"{res.row_value('timepoints', 0, 'amount_1'):.4f}")
    print("timepoint count:", res.values["timepoint_conc.timepoint_count"])


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
