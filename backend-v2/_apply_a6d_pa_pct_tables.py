"""One-off: add "Cumulative drug release µg/cm2" and "Cumulative % drug release" (TPL-A6D-0002).

Hidden helpers added to `timepoints` (row-level, across the cells in use):
  sqrt_min          = sqrt(time_min)                      (x-axis, √T in min)
  pa_mean/sd/rsd    = mean / SD / %RSD of per_area_1..10   (µg/cm²)
  pct_mean/sd/rsd   = mean / SD / %RSD of released_pct_1..10
`released_pct_n` now follows the sheet:
  cumulative / 1000 x avg weight / label claim / sample weight x 100
(sample weight = Cell Loading weight of that cell; avg weight and label claim
from Additional Info). Its 2-dp storage rounding is dropped; the table shows 2 dp.

Two read-only view sections after "Cumulative drug release (µg)", each a
singleton whose own fields hold the per-cell summary rows:
  µg/cm²: Slope = slope(per_area_n, sqrt_min), Correlation (r), r²
  %     : Correlation (r), r²
Release Rate (flux, µg/cm²/√h) is unchanged.

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
CELLS = range(1, 11)

SHEET = [
    (40, 1069016, 688177, 1058932, 1274902, 749441, 1082016),
    (80, 1501219, 1072893, 1466796, 1754152, 1042199, 1498375),
    (120, 1772227, 1366683, 1706687, 2156378, 1245758, 1773041),
    (160, 1883830, 1564759, 1850820, 2338036, 1300307, 1881978),
    (200, 1962798, 1749653, 1935150, 2371001, 1397948, 1959299),
    (240, 2015676, 1839654, 1991104, 2521117, 1402166, 2014489),
]
WEIGHTS = [257.0, 229.4, 227.0, 218.2, 254.3, 257.2]
# √T, cells 1-6, average, SD, %RSD
WANT_PA = [
    (6.3, 76.900, 48.745, 76.155, 92.121, 53.274, 77.861, 70.843, 16.516, 23.31),
    (8.9, 119.839, 84.150, 117.187, 140.713, 82.528, 119.766, 110.697, 22.835, 20.63),
    (11.0, 155.425, 116.897, 150.109, 188.671, 108.280, 155.592, 145.829, 29.285, 20.08),
    (12.6, 182.088, 145.670, 178.486, 224.571, 125.165, 182.067, 173.008, 34.321, 19.84),
    (14.1, 207.518, 175.561, 203.963, 251.397, 145.812, 207.356, 198.601, 35.468, 17.86),
    (15.5, 231.853, 200.389, 228.233, 287.231, 160.584, 231.824, 223.352, 41.751, 18.69),
]
WANT_PA_SLOPE = (16.850, 16.667, 16.572, 21.225, 11.762, 16.757)
WANT_R = (0.9999, 0.9975, 0.9997, 0.9990, 0.9995, 0.9998)
WANT_R2 = (0.9998, 0.9950, 0.9995, 0.9979, 0.9990, 0.9996)
WANT_PCT = [
    (6.3, 5.27, 3.74, 5.90, 7.43, 3.69, 5.33, 5.23, 1.408, 26.94),
    (8.9, 8.21, 6.46, 9.09, 11.35, 5.71, 8.20, 8.17, 1.997, 24.45),
    (11.0, 10.64, 8.97, 11.64, 15.22, 7.49, 10.65, 10.77, 2.629, 24.41),
    (12.6, 12.47, 11.18, 13.84, 18.11, 8.66, 12.46, 12.79, 3.140, 24.56),
    (14.1, 14.21, 13.47, 15.81, 20.28, 10.09, 14.19, 14.68, 3.335, 22.72),
    (15.5, 15.88, 15.37, 17.70, 23.17, 11.11, 15.86, 16.52, 3.923, 23.76),
]


def _series(prefix: str) -> str:
    return "[" + ", ".join(f"{prefix}_{n}" for n in CELLS) + "]"


def _view_group(key, label, value_prefix, band_digits, stat_prefix, stat_digits, summary):
    """summary: list of (field prefix, row label, expression template, digits)."""
    columns = [{"key": "sqrt_min", "label": "Time(√T) in Min.", "digits": 1}]
    columns += [{"key": f"{value_prefix}_{n}", "label": f"Cell-{n}", "digits": band_digits,
                 "showIf": f"cells.cell_no[{n - 1}]"} for n in CELLS]
    columns += [
        {"key": f"{stat_prefix}_mean", "label": "Average (A2-A7)", "digits": stat_digits[0]},
        {"key": f"{stat_prefix}_sd", "label": "SD", "digits": stat_digits[1]},
        {"key": f"{stat_prefix}_rsd", "label": "%RSD", "digits": stat_digits[2]},
    ]
    fields, footer = [], []
    for prefix, row_label, expr, digits in summary:
        values = {}
        for n in CELLS:
            fields.append({"key": f"{prefix}_{n}", "kind": "calculated",
                           "label": f"Cell {n} {row_label}", "expression": expr.format(n=n),
                           "hidden": True})
            values[f"{value_prefix}_{n}"] = f"{key}.{prefix}_{n}"
        footer.append({"label": row_label, "digits": digits, "values": values})
    return {"key": key, "kind": "singleton", "label": label, "fields": fields,
            "view": {"sourceGroup": "timepoints", "columns": columns, "footer": footer}}


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    keys = [g["key"] for g in new["groups"]]
    assert "timepoint_pa" not in keys, "already applied"
    tp = next(g for g in new["groups"] if g["key"] == "timepoints")

    for f in tp["fields"]:
        if f["key"].startswith("released_pct_"):
            n = int(f["key"].rsplit("_", 1)[1])
            f["expression"] = (f"cumulative_{n} / 1000 * avg_weight_mg / label_claim "
                               f"/ cells.weight_mg[{n - 1}] * 100")
            f.pop("rounding", None)

    tp["fields"].append({"key": "sqrt_min", "kind": "calculated", "label": "√Time", "unit": "√min",
                         "expression": "sqrt(time_min)", "hidden": True})
    for stat, src in (("pa", "per_area"), ("pct", "released_pct")):
        for fn, suffix in (("mean", "mean"), ("sd", "sd"), ("rsd", "rsd")):
            tp["fields"].append({"key": f"{stat}_{suffix}", "kind": "calculated",
                                 "label": f"{stat} {suffix}", "expression": f"{fn}({_series(src)})",
                                 "hidden": True})

    pa = _view_group(
        "timepoint_pa", "Cumulative drug release µg/cm2", "per_area", 3, "pa", (3, 3, 2),
        [("slope", "Slope", "slope(timepoints.per_area_{n}, timepoints.sqrt_min)", 3),
         ("r", "Correlation( r )", "correl(timepoints.per_area_{n}, timepoints.sqrt_min)", 4),
         ("r2", "r²", "correl(timepoints.per_area_{n}, timepoints.sqrt_min) ^ 2", 4)],
    )
    pct = _view_group(
        "timepoint_pct",
        "Cumulative % drug release= ( Cumulative drug release/1000*Avg.weight/Label Claim/sample weight*100)",
        "released_pct", 2, "pct", (2, 3, 2),
        [("r", "Correlation( r )", "correl(timepoints.released_pct_{n}, timepoints.sqrt_min)", 4),
         ("r2", "r²", "correl(timepoints.released_pct_{n}, timepoints.sqrt_min) ^ 2", 4)],
    )
    at = keys.index("timepoint_cumulative") + 1
    new["groups"][at:at] = [pa, pct]
    return new


def _groups(definition: dict) -> dict:
    lin = [dict(r) for r in next(g for g in definition["groups"] if g["key"] == "linearity")["rows"]["seed"]]
    for r, a in zip(lin, [200754, 974514, 2922207, 5786622, 7842177, 11507227]):
        r["area"] = a
    cells = [{"cell_no": f"Cell {n}", "weight_mg": w} for n, w in enumerate(WEIGHTS, 1)]
    tp = [{"time_min": s[0], **{f"area_{n}": s[n] for n in range(1, 7)}} for s in SHEET]
    return {"linearity": lin, "cells": cells, "timepoints": tp}


def check(old_def: dict, new_def: dict) -> None:
    new_p = TemplateDefinition.parse(new_def)
    ev_new = WorksheetEvaluator(new_p)
    ev_old = WorksheetEvaluator(TemplateDefinition.parse(old_def))
    assert ev_new.evaluate({}, {}).has_blocking_failure is False
    assert new_p.result_ref == "flux.mean_flux"
    ctx = {"label_claim": 1}  # from the TRF on a real worksheet; 1 % on the sheet
    res = ev_new.evaluate(ctx, _groups(new_def))
    print("context used: avg_weight_mg", res.values.get("avg_weight_mg"),
          "label_claim", res.values.get("label_claim"), "donor_area", res.values.get("donor_area"))

    groups = {g["key"]: g for g in new_def["groups"]}
    bad = []
    for gkey, want_rows, want_summary in (
        ("timepoint_pa", WANT_PA, {"slope": WANT_PA_SLOPE, "r": WANT_R, "r2": WANT_R2}),
        ("timepoint_pct", WANT_PCT, {"r": WANT_R, "r2": WANT_R2}),
    ):
        view = groups[gkey]["view"]
        cols = [c for c in view["columns"] if not c.get("showIf") or int(c["showIf"][-2]) < 6]
        for i, want in enumerate(want_rows):
            for c, w in zip(cols, want):
                got = round(res.row_value("timepoints", i, c["key"]), c["digits"])
                if got != w:
                    bad.append((gkey, i, c["key"], got, w))
        for row in view["footer"]:
            prefix = next(k for k in want_summary if row["values"]["%s_1" % cols[1]["key"].rsplit("_", 1)[0]].endswith(f".{k}_1"))
            for n in range(1, 7):
                ref = row["values"][f"{cols[1]['key'].rsplit('_', 1)[0]}_{n}"]
                got = round(res.values[ref], row["digits"])
                if got != want_summary[prefix][n - 1]:
                    bad.append((gkey, row["label"], n, got, want_summary[prefix][n - 1]))
    for b in bad:
        print("MISMATCH", b)
    assert not bad, f"{len(bad)} mismatches"
    print("µg/cm² table: 60 values + slope/r/r² match the sheet")
    print("% table: 60 values + r/r² match the sheet")

    old = ev_old.evaluate(ctx, _groups(old_def))
    assert all(old.values[k] == res.values[k] for k in old.values if k.startswith("flux."))
    print("Release Rate unchanged:", res.values["flux.mean_flux"], "µg/cm²/√h")


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
