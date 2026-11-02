"""One-off: add the "Drug release profile" graph below "Cumulative % drug release" (TPL-A6D-0002).

Line chart over the `timepoints` rows:
  X = sqrt_min (√T, min^1/2), Y = pa_mean (Average µg/cm² across the cells in use).
Editable graph title (default "Drug release profile"); the series is named
after the worksheet's Batch No. (`batch_no`, LE6001 on the sheet). UI-only:
no new calculation.

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
TITLE = "Drug release profile"
SHEET = [
    (40, 1069016, 688177, 1058932, 1274902, 749441, 1082016),
    (80, 1501219, 1072893, 1466796, 1754152, 1042199, 1498375),
    (120, 1772227, 1366683, 1706687, 2156378, 1245758, 1773041),
    (160, 1883830, 1564759, 1850820, 2338036, 1300307, 1881978),
    (200, 1962798, 1749653, 1935150, 2371001, 1397948, 1959299),
    (240, 2015676, 1839654, 1991104, 2521117, 1402166, 2014489),
]
WANT_POINTS = [(6.3, 70.843), (8.9, 110.697), (11.0, 145.829), (12.6, 173.008), (14.1, 198.601), (15.5, 223.352)]


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    keys = [g["key"] for g in new["groups"]]
    assert "release_chart" not in keys, "already applied"
    group = {
        "key": "release_chart",
        "kind": "singleton",
        "label": TITLE,
        "fields": [
            {"key": "title", "kind": "input", "type": "text", "label": "Graph Title", "default": TITLE},
        ],
        "chart": {
            "title": TITLE,
            "titleField": "title",
            "type": "line",
            "legend": True,
            "sourceGroup": "timepoints",
            "xField": "sqrt_min",
            "xLabel": "Time (Min^1/2)",
            "yLabel": "Drug release (µg)/cm²",
            "series": [{"key": "pa_mean", "label": "Average", "labelRef": "batch_no"}],
            "defaultSeries": ["pa_mean"],
        },
    }
    at = keys.index("timepoint_pct") + 1
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
    res = ev.evaluate({"label_claim": 1}, {"linearity": lin, "cells": cells, "timepoints": tp})
    chart = next(g for g in definition["groups"] if g["key"] == "release_chart")["chart"]
    pts = [(round(res.row_value("timepoints", i, chart["xField"]), 1),
            round(res.row_value("timepoints", i, "pa_mean"), 3)) for i in range(6)]
    assert pts == WANT_POINTS, pts
    print("plotted points match the sheet:", pts)
    print("legend label (batch_no):", res.values.get("batch_no"))


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
