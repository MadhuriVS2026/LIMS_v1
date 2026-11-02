"""One-off: simplify the timepoints section of TPL-A6D-0002.

* Deletes the `sampling_details` group (no formula references it).
* `timepoints` is relabelled "Sampling-Timepoints table" and shows only
  Time Min | Cell-1 .. Cell-6 (area inputs). Every calculated column (conc,
  amount, carry-over, cumulative, per-area, % released, √time, mean, %RSD) is
  marked hidden: still calculated, still feeding Release Rate / flux, not shown.
* Rows: add/delete, min 2 (a release-rate slope needs two points), max 20,
  opening with 6 rows seeded with Time Min 40, 80, 120, 160, 200, 240.
  Areas stay blank.

Writes test_templates.definition (id=43) and drops `sampling_details` from
stored worksheet values. Take a lims.db backup before running without
--validate-only.
"""
import argparse
import copy
import json
import sqlite3

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

DB = r"d:\RD-instance\GIT\backend-v2\lims.db"
CODE = "TPL-A6D-0002"
TIMES = [40, 80, 120, 160, 200, 240]
#  User's sheet (Indian digit grouping: 10,69,016 = 1069016).
SHEET = [
    (40, 1069016, 688177, 1058932, 1274902, 749441, 1082016),
    (80, 1501219, 1072893, 1466796, 1754152, 1042199, 1498375),
    (120, 1772227, 1366683, 1706687, 2156378, 1245758, 1773041),
    (160, 1883830, 1564759, 1850820, 2338036, 1300307, 1881978),
    (200, 1962798, 1749653, 1935150, 2371001, 1397948, 1959299),
    (240, 2015676, 1839654, 1991104, 2521117, 1402166, 2014489),
]


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    keys = [g["key"] for g in new["groups"]]
    assert "sampling_details" in keys, "already applied"
    assert "sampling_details." not in json.dumps(new), "sampling_details is referenced"
    new["groups"] = [g for g in new["groups"] if g["key"] != "sampling_details"]

    tp = next(g for g in new["groups"] if g["key"] == "timepoints")
    tp["label"] = "Sampling-Timepoints table"
    tp["rows"] = {"min": 2, "max": 20, "default": 6, "labelFrom": "time_min",
                  "seed": [{"time_min": t} for t in TIMES]}
    for f in tp["fields"]:
        if f["key"] == "time_min":
            f["label"] = "Time Min"
            f.pop("unit", None)
        elif f["kind"] == "area" and f["key"].startswith("area_"):
            f["label"] = f"Cell-{f['key'].split('_')[1]}"
        elif f["kind"] == "calculated":
            f["hidden"] = True
    return new


def check(old_def: dict, new_def: dict) -> None:
    new_p = TemplateDefinition.parse(new_def)
    assert new_p.result_ref == "flux.mean_flux"
    ev_old, ev_new = WorksheetEvaluator(TemplateDefinition.parse(old_def)), WorksheetEvaluator(new_p)
    assert ev_new.evaluate({}, {}).has_blocking_failure is False

    tp_new = next(g for g in new_def["groups"] if g["key"] == "timepoints")
    visible = [f["key"] for f in tp_new["fields"] if not f.get("hidden")]
    assert visible == ["time_min"] + [f"area_{n}" for n in range(1, 7)], visible
    print("visible columns:", [f.get("label") for f in tp_new["fields"] if not f.get("hidden")])

    lin = [dict(r) for r in next(g for g in new_def["groups"] if g["key"] == "linearity")["rows"]["seed"]]
    for r, a in zip(lin, [200754, 974514, 2922207, 5786622, 7842177, 11507227]):
        r["area"] = a
    cells = [{"cell_no": f"Cell {n}", "weight_mg": w}
             for n, w in enumerate([257.0, 229.4, 227.0, 218.2, 254.3, 257.2], 1)]
    tp = [{"time_min": s[0], **{f"area_{n}": s[n] for n in range(1, 7)}} for s in SHEET]
    ctx = {"label_claim": 1}
    groups = {"linearity": lin, "cells": cells, "timepoints": tp}
    r_old = ev_old.evaluate(ctx, groups)
    r_new = ev_new.evaluate(ctx, groups)
    flux_keys = [k for k in r_new.values if k.startswith("flux.")]
    assert all(r_old.values[k] == r_new.values[k] for k in flux_keys)
    print("Release Rate identical before/after with your areas:",
          {k.split(".")[1]: r_new.values[k] for k in ("flux.mean_flux", "flux.rsd_flux", "flux.min_fit")})

    #  A 7th timepoint the analyst adds is used in the release-rate fit.
    tp7 = tp + [{"time_min": 300, **{f"area_{n}": SHEET[-1][n] + 40000 for n in range(1, 7)}}]
    r7 = ev_new.evaluate(ctx, {**groups, "timepoints": tp7})
    assert r7.values["flux.mean_flux"] != r_new.values["flux.mean_flux"]
    print("7th timepoint included: mean flux", r_new.values["flux.mean_flux"], "->", r7.values["flux.mean_flux"])


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

    migrations = []
    for wid, gv_raw in db.execute("select id, group_values from test_worksheets where template_id=?", (tid,)):
        gv = json.loads(gv_raw) if gv_raw else {}
        if "sampling_details" in gv:
            dropped = gv.pop("sampling_details")
            assert all(v is None for r in dropped for v in r.values()), f"worksheet {wid} has sample weights: {dropped}"
            migrations.append((wid, gv))
            print(f"worksheet {wid}: removed empty sampling_details")

    if args.validate_only:
        print("--validate-only: no DB write")
        return
    db.execute("update test_templates set definition=? where id=?", (json.dumps(new), tid))
    for wid, gv in migrations:
        db.execute("update test_worksheets set group_values=? where id=?", (json.dumps(gv), wid))
    db.commit()
    assert json.loads(db.execute("select definition from test_templates where id=?", (tid,)).fetchone()[0]) == new
    assert db.execute("select status from test_templates where id=?", (tid,)).fetchone()[0] == status
    print("written and re-read byte-equal; status:", status)


if __name__ == "__main__":
    main()
