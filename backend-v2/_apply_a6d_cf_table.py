"""One-off: add "Sample-Timepoints-Correction factor" below the concentration table (TPL-A6D-0002).

* `timepoints` gains hidden calculated cf_1..cf_10:
    first timepoint            -> 0
    later timepoints           -> previous timepoint's amount_n x sample withdrawn
                                  (replacement_volume, mL) / cell volume
                                  (receptor_volume, mL)
  blank for cells not listed in Cell Loading. Placed after amount_n so they are
  evaluated after it. Nothing else reads them, so no result changes.
* New read-only view `timepoint_cf` (Time in Min | Cell-1..10, 4 decimals),
  rows following the Sampling-Timepoints table, Cell-n following Cell Loading.

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
TITLE = "Sample-Timepoints-Correction factor"
BAND = ("Correction factor(1st time point) = Amount released at specified time point x "
        "Sample withdrawn (in ml) / Cell volume (in ml)")
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
    (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    (19.3349, 12.2558, 19.1475, 23.1619, 13.3946, 19.5765),
    (27.3688, 19.4070, 26.7289, 32.0703, 18.8364, 27.3159),
    (32.4063, 24.8680, 31.1880, 39.5470, 22.6202, 32.4214),
    (34.4808, 28.5499, 33.8672, 42.9237, 23.6342, 34.4464),
    (35.9487, 31.9867, 35.4348, 43.5364, 25.4491, 35.8836),
]


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    keys = [g["key"] for g in new["groups"]]
    assert "timepoint_cf" not in keys, "already applied"
    tp = next(g for g in new["groups"] if g["key"] == "timepoints")

    cf_fields = [
        {
            "key": f"cf_{n}",
            "kind": "calculated",
            "label": f"Cell {n} Correction factor",
            "unit": "µg",
            "expression": (
                f"if(isblank(cells.cell_no[{n - 1}]), blank(), "
                f"if(rowno = 1, 0, prev.amount_{n} * replacement_volume / receptor_volume))"
            ),
            "hidden": True,
        }
        for n in CELLS
    ]
    last_amount = max(i for i, f in enumerate(tp["fields"]) if f["key"].startswith("amount_"))
    tp["fields"][last_amount + 1:last_amount + 1] = cf_fields

    columns = [{"key": "time_min", "label": "Time in Min", "digits": 1}] + [
        {"key": f"cf_{n}", "label": f"Cell-{n}", "digits": 4,
         "showIf": f"cells.cell_no[{n - 1}]", "band": BAND}
        for n in CELLS
    ]
    group = {
        "key": "timepoint_cf",
        "kind": "singleton",
        "label": TITLE,
        "fields": [
            {"key": "timepoint_count", "kind": "calculated", "label": "Timepoints",
             "expression": "count(timepoints.time_min)", "hidden": True},
        ],
        "view": {"sourceGroup": "timepoints", "columns": columns},
    }
    at = keys.index("timepoint_conc") + 1
    new["groups"][at:at] = [group]
    return new


def _groups(definition: dict, n_cells: int) -> dict:
    lin = [dict(r) for r in next(g for g in definition["groups"] if g["key"] == "linearity")["rows"]["seed"]]
    for r, a in zip(lin, [200754, 974514, 2922207, 5786622, 7842177, 11507227]):
        r["area"] = a
    cells = [{"cell_no": f"Cell {n}", "weight_mg": 250} for n in range(1, n_cells + 1)]
    tp = [{"time_min": s[0], **{f"area_{n}": s[n] for n in range(1, 7)}} for s in SHEET]
    return {"linearity": lin, "cells": cells, "timepoints": tp}


def check(old_def: dict, new_def: dict) -> None:
    new_p = TemplateDefinition.parse(new_def)
    ev_old, ev_new = WorksheetEvaluator(TemplateDefinition.parse(old_def)), WorksheetEvaluator(new_p)
    assert ev_new.evaluate({}, {}).has_blocking_failure is False
    assert new_p.result_ref == "flux.mean_flux"

    res = ev_new.evaluate({}, _groups(new_def, 6))
    bad = [(SHEET[i][0], n, round(res.row_value("timepoints", i, f"cf_{n}"), 4), WANT[i][n - 1])
           for i in range(6) for n in range(1, 7)
           if round(res.row_value("timepoints", i, f"cf_{n}"), 4) != WANT[i][n - 1]]
    assert not bad, bad
    print("all 36 correction factors match the sheet to 4 decimals; 80 min Cell-1 =",
          f"{res.row_value('timepoints', 1, 'cf_1'):.4f}")

    old = ev_old.evaluate({}, _groups(old_def, 6))
    assert all(old.values[k] == res.values[k] for k in old.values if k.startswith("flux."))
    print("Release Rate unchanged:", res.values["flux.mean_flux"])

    #  Unused cell: blank, including the first timepoint.
    from src.domain.services.calculation.expression import EMPTY
    assert res.row_value("timepoints", 0, "cf_7") is EMPTY and res.row_value("timepoints", 3, "cf_7") is EMPTY
    print("cell 7 (not in Cell Loading): blank: OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    db = sqlite3.connect(DB)
    tid, status, raw = db.execute(
        "select id, status, definition from test_templates where code=?", (CODE,)
    ).fetchone()
    old = json.loads(raw)
    new = mutate(old)
    check(old, new)
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
