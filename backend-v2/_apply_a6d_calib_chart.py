"""One-off: calibration curve chart + regression box below the linearity table (TPL-A6D-0002).

* New `calibration_chart` singleton right after `linearity`: scatter of Area
  Response vs Theoretical concentration over the calibration-standard rows,
  with the fitted line, its equation and R² (editable graph title).
* `curve` (Slope / Intercept / Correlation) moves to just below the chart;
  intercept now rounds to 1 decimal to match the sheet; adds a hidden r_squared
  for the chart label. Evaluation order is dependency-based, so moving the group
  changes no calculation.
* `is_standard` = any row that is not LQC/MQC/HQC, so standards the analyst adds
  join the fit and the chart automatically. Both masks are marked hidden.

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
TITLE = "Calibration Curve (Tapinarof)"
MASKED = "where(linearity.area, linearity.is_standard), where(linearity.theoretical_ppm, linearity.is_standard)"

AREAS = [200754, 974514, 2922207, 5786622, 7842177, 11507227]
EXPECT_OBS = [3.195478386, 17.57827346, 53.7823539, 107.0266337, 145.2356731, 213.3623055]


def grp(defn: dict, key: str) -> dict:
    return next(g for g in defn["groups"] if g["key"] == key)


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    keys = [g["key"] for g in new["groups"]]
    assert "calibration_chart" not in keys, "already applied"

    lin = grp(new, "linearity")
    for f in lin["fields"]:
        if f["key"] == "is_standard":
            f["expression"] = (
                'not ((calibration_curve = "LQC") or (calibration_curve = "MQC") '
                'or (calibration_curve = "HQC"))'
            )
            f["hidden"] = True
        elif f["key"] == "is_qc":
            f["hidden"] = True

    curve = grp(new, "curve")
    for f in curve["fields"]:
        if f["key"] == "curve_intercept":
            f["rounding"] = {"mode": "round", "digits": 1}
    curve["fields"].append({
        "key": "r_squared",
        "kind": "calculated",
        "label": "R²",
        "expression": f"correl({MASKED}) * correl({MASKED})",
        "rounding": {"mode": "round", "digits": 4},
        "hidden": True,
    })

    chart = {
        "key": "calibration_chart",
        "kind": "singleton",
        "label": "Calibration Curve",
        "fields": [
            {"key": "title", "kind": "input", "type": "text", "label": "Graph Title", "default": TITLE},
        ],
        "chart": {
            "title": TITLE,
            "titleField": "title",
            "type": "scatter",
            "sourceGroup": "linearity",
            "xField": "theoretical_ppm",
            "xLabel": "Concentration",
            "yLabel": "Area Response",
            "series": [{"key": "area", "label": "Calibration standards"}],
            "defaultSeries": ["area"],
            "rowFilter": "is_standard",
            "trendline": {
                "slopeRef": "curve.curve_slope",
                "interceptRef": "curve.curve_intercept",
                "r2Ref": "curve.r_squared",
            },
        },
    }

    groups = [g for g in new["groups"] if g["key"] != "curve"]
    at = [g["key"] for g in groups].index("linearity") + 1
    groups[at:at] = [chart, curve]
    new["groups"] = groups
    return new


def lin_rows(definition: dict, extra: list[dict] | None = None) -> list[dict]:
    rows = [dict(r) for r in grp(definition, "linearity")["rows"]["seed"]]
    for r, a in zip(rows, AREAS):
        r["area"] = a
    #  QC rows get skewing areas: they must not move the fit.
    for r in rows[6:]:
        r["area"] = 9_000_000
    return rows + (extra or [])


def check(definition: dict) -> None:
    parsed = TemplateDefinition.parse(definition)
    ev = WorksheetEvaluator(parsed)
    assert ev.evaluate({}, {}).has_blocking_failure is False
    assert parsed.result_ref == "flux.mean_flux"

    res = ev.evaluate({}, {"linearity": lin_rows(definition)})
    v = res.values
    print("slope", v["curve.curve_slope"], "intercept", v["curve.curve_intercept"],
          "correlation", v["curve.correlation"], "r2", v["curve.r_squared"])
    assert v["curve.curve_slope"] == 53797.61 and v["curve.curve_intercept"] == 28844.9
    assert v["curve.correlation"] == 0.9999 and v["curve.r_squared"] == 0.9998
    mask = [res.row_value("linearity", i, "is_standard") for i in range(9)]
    assert mask == [True] * 6 + [False] * 3, mask
    obs = [res.row_value("linearity", i, "observed_ppm") for i in range(6)]
    assert all(abs(o - e) < 1e-3 for o, e in zip(obs, EXPECT_OBS)), obs
    print("observed ppm still match the sheet:", [round(o, 4) for o in obs])

    #  Dynamic: a 7th standard the analyst adds joins the fit.
    extra = [{"calibration_curve": "Calibration standard-7", "concentration_pct": 80,
              "std_weight_mg": 89.73, "diluted_to_ml_1": 50, "ml_a": 1, "ml_b": 1,
              "ml_taken": 8, "diluted_to_ml_2": 50, "area": 15_400_000}]
    res7 = ev.evaluate({}, {"linearity": lin_rows(definition, extra)})
    assert res7.row_value("linearity", 9, "is_standard") is True
    assert res7.values["curve.curve_slope"] != 53797.61
    print("7th standard included in fit: slope ->", res7.values["curve.curve_slope"])

    #  A blank added row doesn't break the fit.
    resb = ev.evaluate({}, {"linearity": lin_rows(definition, [{}])})
    assert resb.values["curve.curve_slope"] == 53797.61
    print("blank added row ignored: OK")


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
    back = json.loads(db.execute("select definition from test_templates where id=?", (tid,)).fetchone()[0])
    assert back == new
    assert db.execute("select status from test_templates where id=?", (tid,)).fetchone()[0] == status
    print("written and re-read byte-equal; status:", status)


if __name__ == "__main__":
    main()
