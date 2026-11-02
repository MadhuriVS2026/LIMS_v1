"""One-off: replace "Cell Loading" with a "Cell Loading details" table (TPL-A6D-0002).

`cells` changes from a singleton of six "Cell n Applied Dose" inputs to a
sequence table with Cell no | Weight (mg) (the form's row-number column is the
Sr No). Opens with Cell 1..Cell 6, weights blank; add/edit/delete rows (1..12).

The per-cell % Released formulas read the weight of their own row:
cells.applied_mg_n  ->  cells.weight_mg[n-1]   (0-based row index)

Existing worksheets on this template store the old one-row layout with no
weights entered; they are converted to the six seeded rows.

Writes test_templates.definition (id=43) and test_worksheets.group_values.
Take a lims.db backup before running without --validate-only.
"""
import argparse
import copy
import json
import re
import sqlite3

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

DB = r"d:\RD-instance\GIT\backend-v2\lims.db"
CODE = "TPL-A6D-0002"
SEED = [{"cell_no": f"Cell {n}"} for n in range(1, 7)]
SHEET_WEIGHTS = [257.0, 229.4, 227.0, 218.2, 254.3, 257.2]


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    cells = next(g for g in new["groups"] if g["key"] == "cells")
    assert cells["kind"] == "singleton", "already applied"

    cells.clear()
    cells.update({
        "key": "cells",
        "kind": "sequence",
        "label": "Cell Loading details",
        "rows": {"min": 1, "max": 12, "default": 6, "labelFrom": "cell_no", "seed": copy.deepcopy(SEED)},
        "fields": [
            {"key": "cell_no", "kind": "input", "type": "text", "label": "Cell no"},
            {"key": "weight_mg", "kind": "input", "type": "number", "label": "Weight", "unit": "mg"},
        ],
    })

    def repoint(expr: str) -> str:
        return re.sub(r"cells\.applied_mg_(\d+)", lambda m: f"cells.weight_mg[{int(m.group(1)) - 1}]", expr)

    changed = 0
    for g in new["groups"]:
        for f in g.get("fields", []):
            e = f.get("expression")
            if e and "cells.applied_mg_" in e:
                f["expression"] = repoint(e)
                changed += 1
    assert changed == 6, changed
    assert "applied_mg_" not in json.dumps(new), "a reference to the old fields remains"
    return new


def check(old_def: dict, new_def: dict) -> None:
    old_p, new_p = TemplateDefinition.parse(old_def), TemplateDefinition.parse(new_def)
    ev_old, ev_new = WorksheetEvaluator(old_p), WorksheetEvaluator(new_p)
    assert ev_new.evaluate({}, {}).has_blocking_failure is False
    assert new_p.result_ref == "flux.mean_flux"

    #  Same data through old and new layouts must give the same % Released.
    ctx = {"label_claim": 1}
    tp = [{"time_min": t, **{f"area_{n}": 200000 + 150000 * i + 9000 * n for n in range(1, 7)}}
          for i, t in enumerate([40, 80, 120, 160, 200, 240])]
    lin = [dict(r) for r in next(g for g in new_def["groups"] if g["key"] == "linearity")["rows"]["seed"]]
    for r, a in zip(lin, [200754, 974514, 2922207, 5786622, 7842177, 11507227]):
        r["area"] = a
    old_cells = [{f"applied_mg_{n}": w for n, w in enumerate(SHEET_WEIGHTS, 1)}]
    new_cells = [{"cell_no": f"Cell {n}", "weight_mg": w} for n, w in enumerate(SHEET_WEIGHTS, 1)]
    r_old = ev_old.evaluate(ctx, {"linearity": lin, "cells": old_cells, "timepoints": tp})
    r_new = ev_new.evaluate(ctx, {"linearity": lin, "cells": new_cells, "timepoints": tp})
    for i in range(6):
        for n in range(1, 7):
            a = r_old.row_value("timepoints", i, f"released_pct_{n}")
            b = r_new.row_value("timepoints", i, f"released_pct_{n}")
            assert a == b and a not in (None, ""), (i, n, a, b)
    print("% Released identical to the old layout for all 6 cells x 6 timepoints, e.g.",
          [r_new.row_value("timepoints", 5, f"released_pct_{n}") for n in range(1, 7)])
    assert r_old.values.get("flux.mean_flux") == r_new.values.get("flux.mean_flux")
    print("flux unchanged:", r_new.values.get("flux.mean_flux"))


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
        stored = gv.get("cells")
        if stored and any(k.startswith("applied_mg_") for r in stored for k in r):
            weights = [stored[0].get(f"applied_mg_{n}") for n in range(1, 7)]
            gv["cells"] = [
                {"cell_no": f"Cell {n}", **({"weight_mg": w} if w is not None else {})}
                for n, w in enumerate(weights, 1)
            ]
            migrations.append((wid, gv))
            print(f"worksheet {wid}: cells -> {gv['cells']}")

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
