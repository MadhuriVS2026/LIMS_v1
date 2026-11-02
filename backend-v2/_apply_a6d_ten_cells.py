"""One-off: let TPL-A6D-0002 handle up to 10 Franz cells, driven by "Cell Loading details".

* `cells` (Cell Loading details): max rows 10.
* `timepoints`: per-cell fields for cells 1..10 (area, conc, amount, carry-over,
  cumulative, per-area, % released). Cell n is used only while row n of the
  Cell Loading table has a Cell no: conc_n is blank otherwise, so everything
  downstream of it is blank and drops out of means / %RSD / flux.
  Area column n carries `showIf: cells.cell_no[n-1]` (UI hint: shown only then).
* `flux` (Release Rate): flux_n / fit_n for 1..10 with the same showIf; mean,
  %RSD and poorest fit now span all 10 (blanks are skipped).

Writes ONLY the `definition` column. Take a lims.db backup before running
without --validate-only.
"""
import argparse
import copy
import json
import sqlite3

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.expression import EMPTY
from src.domain.services.calculation.template_schema import TemplateDefinition

DB = r"d:\RD-instance\GIT\backend-v2\lims.db"
CODE = "TPL-A6D-0002"
MAX_CELLS = 10
CELLS = range(1, MAX_CELLS + 1)
PER_CELL_TP = ("amount", "carry", "cumulative", "per_area", "released_pct")

SHEET = [
    (40, 1069016, 688177, 1058932, 1274902, 749441, 1082016),
    (80, 1501219, 1072893, 1466796, 1754152, 1042199, 1498375),
    (120, 1772227, 1366683, 1706687, 2156378, 1245758, 1773041),
    (160, 1883830, 1564759, 1850820, 2338036, 1300307, 1881978),
    (200, 1962798, 1749653, 1935150, 2371001, 1397948, 1959299),
    (240, 2015676, 1839654, 1991104, 2521117, 1402166, 2014489),
]
WEIGHTS = [257.0, 229.4, 227.0, 218.2, 254.3, 257.2]


def _for_cell(template: dict, n: int) -> dict:
    """Copy a cell-6 field as cell n (keys, labels, row index of the weight)."""
    s = json.dumps(template, ensure_ascii=False)
    s = s.replace("_6", f"_{n}").replace("Cell 6", f"Cell {n}").replace("[5]", f"[{n - 1}]")
    return json.loads(s)


def _series(prefix: str) -> str:
    return "[" + ", ".join(f"{prefix}_{n}" for n in CELLS) + "]"


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    g = {x["key"]: x for x in new["groups"]}
    tp, flux, cells = g["timepoints"], g["flux"], g["cells"]
    assert not any(f["key"] == "area_7" for f in tp["fields"]), "already applied"

    cells["rows"]["max"] = MAX_CELLS

    by = {f["key"]: f for f in tp["fields"]}
    fields = [by["time_min"]]
    for n in CELLS:
        area = _for_cell(by["area_6"], n)
        area["label"] = f"Cell-{n}"
        area["showIf"] = f"cells.cell_no[{n - 1}]"
        fields.append(area)
    fields.append(by["sqrt_hours"])
    for n in CELLS:
        conc = _for_cell(by["conc_6"], n)
        conc["expression"] = (
            f"if(isblank(cells.cell_no[{n - 1}]), blank(), "
            f"(area_{n} - curve.curve_intercept) / curve.curve_slope)"
        )
        fields.append(conc)
    for prefix in PER_CELL_TP:
        fields += [_for_cell(by[f"{prefix}_6"], n) for n in CELLS]
    for key, fn in (("mean_per_area", "mean"), ("rsd_per_area", "rsd")):
        f = copy.deepcopy(by[key])
        f["expression"] = f"{fn}({_series('per_area')})"
        fields.append(f)
    assert len(fields) == 1 + 10 * 7 + 1 + 2, len(fields)
    tp["fields"] = fields

    fb = {f["key"]: f for f in flux["fields"]}
    ffields = []
    for prefix in ("flux", "fit"):
        for n in CELLS:
            f = _for_cell(fb[f"{prefix}_6"], n)
            f["showIf"] = f"cells.cell_no[{n - 1}]"
            ffields.append(f)
    for key, expr in (("mean_flux", f"mean({_series('flux')})"),
                      ("rsd_flux", f"rsd({_series('flux')})"),
                      ("min_fit", f"min({_series('fit')})")):
        f = copy.deepcopy(fb[key])
        f["expression"] = expr
        ffields.append(f)
    flux["fields"] = ffields
    return new


def _groups(definition: dict, n_cells: int, extra_areas: list | None = None) -> dict:
    lin = [dict(r) for r in next(x for x in definition["groups"] if x["key"] == "linearity")["rows"]["seed"]]
    for r, a in zip(lin, [200754, 974514, 2922207, 5786622, 7842177, 11507227]):
        r["area"] = a
    weights = WEIGHTS + [240.0] * 4
    cells = [{"cell_no": f"Cell {n}", "weight_mg": weights[n - 1]} for n in range(1, n_cells + 1)]
    tp = []
    for i, s in enumerate(SHEET):
        row = {"time_min": s[0], **{f"area_{n}": s[n] for n in range(1, 7)}}
        for j, a in enumerate(extra_areas or []):
            row[f"area_{7 + j}"] = a[i]
        tp.append(row)
    return {"linearity": lin, "cells": cells, "timepoints": tp}


def check(old_def: dict, new_def: dict) -> None:
    new_p = TemplateDefinition.parse(new_def)
    assert new_p.result_ref == "flux.mean_flux"
    ev_old, ev_new = WorksheetEvaluator(TemplateDefinition.parse(old_def)), WorksheetEvaluator(new_p)
    assert ev_new.evaluate({}, {}).has_blocking_failure is False
    ctx = {"label_claim": 1}
    pick = ("flux.mean_flux", "flux.rsd_flux", "flux.min_fit")

    #  1. Six cells: identical to today.
    old6 = ev_old.evaluate(ctx, _groups(old_def, 6))
    new6 = ev_new.evaluate(ctx, _groups(new_def, 6))
    assert all(old6.values[k] == new6.values[k] for k in pick)
    for i in range(6):
        for n in range(1, 7):
            assert old6.row_value("timepoints", i, f"released_pct_{n}") == new6.row_value("timepoints", i, f"released_pct_{n}")
    assert new6.values["flux.flux_7"] is EMPTY
    print("6 cells: identical to before ->", {k: new6.values[k] for k in pick})

    #  2. Seven cells: cell 7 flows through to flux and the summaries.
    cell7 = [[int(a * 0.95) for a in (r[1] for r in SHEET)]]
    new7 = ev_new.evaluate(ctx, _groups(new_def, 7, cell7))
    assert new7.values["flux.flux_7"] is not EMPTY
    assert new7.values["flux.mean_flux"] != new6.values["flux.mean_flux"]
    print("7 cells: flux_7", new7.values["flux.flux_7"], "mean flux", new6.values["flux.mean_flux"], "->", new7.values["flux.mean_flux"])

    #  3. Areas typed for cell 7 but no 7th Cell Loading row: ignored.
    stray = ev_new.evaluate(ctx, _groups(new_def, 6, cell7))
    assert stray.values["flux.mean_flux"] == new6.values["flux.mean_flux"]
    print("cell-7 areas without a 7th Cell Loading row are ignored: OK")

    #  4. Ten cells.
    ten = ev_new.evaluate(ctx, _groups(new_def, 10, cell7 * 4))
    assert all(ten.values[f"flux.flux_{n}"] is not EMPTY for n in CELLS)
    print("10 cells: all 10 fluxes computed, mean", ten.values["flux.mean_flux"])


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
