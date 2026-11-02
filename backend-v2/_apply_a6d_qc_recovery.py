"""One-off: add the "% Recovery" bracketing table below the LQC-MQC-HQC table (TPL-A6D-0002).

* `linearity_qc` gains hidden calculated helpers (not shown): theoretical_ppm
  (same dilution formula as the linearity table) and is_lqc / is_mqc / is_hqc.
* New `qc_recovery` sequence, two injections per row, like the sheet:
  Bracketing Standard Solution | Theoretical concentration (ppm) | Area Response |
  Observed concentration (ppm) | % Recovery, then the same five for the second set.
  Rows cycle LQC, MQC, HQC; each row's theoretical concentration is looked up
  from the LQC-MQC-HQC table by that position. Observed uses the calibration
  curve; % Recovery uses unrounded observed and theoretical (as the sheet does).
  Seeded with LQC-1..HQC-3 (left) and LQC-4..HQC-6 (right); add/delete rows.

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
THEO = "std_weight_mg / diluted_to_ml_1 * ml_a / ml_b * ml_taken / diluted_to_ml_2 * potency / 100 * 1000"
ROUND2 = {"mode": "round", "digits": 2}

# (left solution, left area, left observed, left recovery, right ..., right area, observed, recovery)
SHEET = [
    ("LQC-1", 200535, 3.19, 89.21, "LQC-4", 200666, 3.19, 89.28),
    ("MQC-1", 2922913, 53.80, 100.25, "MQC-4", 2920092, 53.74, 100.15),
    ("HQC-1", 5780363, 106.91, 99.62, "HQC-4", 5781894, 106.94, 99.64),
    ("LQC-2", 200058, 3.18, 88.96, "LQC-5", 200214, 3.19, 89.04),
    ("MQC-2", 2920429, 53.75, 100.17, "MQC-5", 2920520, 53.75, 100.17),
    ("HQC-2", 5780508, 106.91, 99.62, "HQC-5", 5773134, 106.78, 99.49),
    ("LQC-3", 199288, 3.17, 88.56, "LQC-6", 200058, 3.18, 88.96),
    ("MQC-3", 2915187, 53.65, 99.98, "MQC-6", 2920429, 53.75, 100.17),
    ("HQC-3", 5769025, 106.70, 99.42, "HQC-6", 5780508, 106.91, 99.62),
]
SHEET_THEO = {"L": 3.58, "M": 53.66, "H": 107.32}


def grp(defn: dict, key: str) -> dict:
    return next(g for g in defn["groups"] if g["key"] == key)


def _qc_theo(label_flag: str) -> str:
    return f"mean(where(linearity_qc.theoretical_ppm, linearity_qc.{label_flag}))"


def side_fields(p: str, solution_label: str, theo_label: str) -> list[dict]:
    observed = f"({p}_area - curve.curve_intercept) / curve.curve_slope"
    return [
        {"key": f"{p}_solution", "kind": "input", "type": "text", "label": solution_label},
        {"key": f"{p}_theoretical_ppm", "kind": "calculated", "label": theo_label, "unit": "ppm",
         "expression": "theo_raw", "rounding": ROUND2},
        {"key": f"{p}_area", "kind": "area", "label": "Area Response", "unit": "µV·s"},
        {"key": f"{p}_observed_ppm", "kind": "calculated", "label": "Observed concentration",
         "unit": "ppm", "expression": observed, "rounding": ROUND2},
        {"key": f"{p}_recovery_pct", "kind": "calculated", "label": "% Recovery", "unit": "%",
         "expression": f"{observed} / theo_raw * 100", "rounding": ROUND2},
    ]


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    keys = [g["key"] for g in new["groups"]]
    assert "qc_recovery" not in keys, "already applied"

    qc = grp(new, "linearity_qc")
    qc["fields"] += [
        {"key": "theoretical_ppm", "kind": "calculated", "label": "Theoretical concentration",
         "unit": "ppm", "expression": THEO, "hidden": True},
        {"key": "is_lqc", "kind": "calculated", "type": "boolean", "label": "Is LQC",
         "expression": 'calibration_curve = "LQC"', "hidden": True},
        {"key": "is_mqc", "kind": "calculated", "type": "boolean", "label": "Is MQC",
         "expression": 'calibration_curve = "MQC"', "hidden": True},
        {"key": "is_hqc", "kind": "calculated", "type": "boolean", "label": "Is HQC",
         "expression": 'calibration_curve = "HQC"', "hidden": True},
    ]

    seed = []
    for i in range(9):
        level = ("LQC", "MQC", "HQC")[i % 3]
        seed.append({"l_solution": f"{level}-{i // 3 + 1}", "r_solution": f"{level}-{i // 3 + 4}"})

    recovery = {
        "key": "qc_recovery",
        "kind": "sequence",
        "label": "% Recovery",
        "rows": {"min": 1, "max": 15, "default": 9, "labelFrom": "l_solution", "seed": seed},
        "fields": [
            #  Position in the LQC, MQC, HQC cycle (1, 2, 3) — hidden helper.
            {"key": "qc_level", "kind": "calculated", "label": "QC level",
             "expression": "rowno - 3 * trunc((rowno - 1) / 3)", "hidden": True},
            {"key": "theo_raw", "kind": "calculated", "label": "Theoretical (unrounded)", "unit": "ppm",
             "expression": (
                 f"if(qc_level = 1, {_qc_theo('is_lqc')}, "
                 f"if(qc_level = 2, {_qc_theo('is_mqc')}, {_qc_theo('is_hqc')}))"
             ),
             "hidden": True},
            *side_fields("l", "Bracketing Standard Solution", "Theoretical concentration"),
            *side_fields("r", "Bracketing Standard Solution", "Theoretical conc."),
        ],
    }
    at = keys.index("linearity_qc") + 1
    new["groups"][at:at] = [recovery]
    return new


def check(definition: dict) -> None:
    parsed = TemplateDefinition.parse(definition)
    ev = WorksheetEvaluator(parsed)
    assert ev.evaluate({}, {}).has_blocking_failure is False
    assert parsed.result_ref == "flux.mean_flux"

    lin = [dict(r) for r in grp(definition, "linearity")["rows"]["seed"]]
    for r, a in zip(lin, [200754, 974514, 2922207, 5786622, 7842177, 11507227]):
        r["area"] = a
    qc = [dict(r) for r in grp(definition, "linearity_qc")["rows"]["seed"]]
    rec = []
    for s in SHEET:
        rec.append({"l_solution": s[0], "l_area": s[1], "r_solution": s[4], "r_area": s[5]})
    res = ev.evaluate({}, {"linearity": lin, "linearity_qc": qc, "qc_recovery": rec})

    bad = []
    for i, s in enumerate(SHEET):
        want_theo = SHEET_THEO[s[0][0]]
        for p, obs, recv in (("l", s[2], s[3]), ("r", s[6], s[7])):
            got = (res.row_value("qc_recovery", i, f"{p}_theoretical_ppm"),
                   res.row_value("qc_recovery", i, f"{p}_observed_ppm"),
                   res.row_value("qc_recovery", i, f"{p}_recovery_pct"))
            if got != (want_theo, obs, recv):
                bad.append((s[0] if p == "l" else s[4], got, (want_theo, obs, recv)))
    assert not bad, bad
    print("all 18 bracketing injections match the sheet (theoretical, observed, % recovery)")
    print("e.g. row 1:", {k: res.row_value("qc_recovery", 0, k) for k in
          ("l_solution", "l_theoretical_ppm", "l_observed_ppm", "l_recovery_pct",
           "r_solution", "r_theoretical_ppm", "r_observed_ppm", "r_recovery_pct")})

    #  Editing a dilution in the LQC-MQC-HQC table flows through.
    qc2 = [dict(r) for r in qc]
    qc2[0]["ml_taken"] = 2
    res2 = ev.evaluate({}, {"linearity": lin, "linearity_qc": qc2, "qc_recovery": rec})
    assert res2.row_value("qc_recovery", 0, "l_theoretical_ppm") == 7.15
    print("LQC dilution change flows into this table: OK (3.58 -> 7.15)")


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
