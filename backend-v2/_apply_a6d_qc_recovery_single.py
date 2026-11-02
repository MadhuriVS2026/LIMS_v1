"""One-off: make the "% Recovery" table one injection per row (TPL-A6D-0002).

Replaces the two side-by-side sets (l_* / r_*) with five columns:
  Bracketing Standard Solution | Theoretical concentration (ppm) | Area Response |
  Observed concentration (ppm) | % Recovery
Seeded with 18 rows: LQC-1, MQC-1, HQC-1 ... LQC-6, MQC-6, HQC-6, so rows still
cycle LQC, MQC, HQC and the theoretical lookup by position is unchanged.
Add/delete rows (1..30). QC recovery limits read the new recovery column.

Also converts stored qc_recovery rows of existing worksheets on this template
(left set first, then right set) so they keep opening/saving.

Writes test_templates.definition for id=43 and test_worksheets.group_values for
the affected worksheets. Take a lims.db backup before running without
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
ROUND2 = {"mode": "round", "digits": 2}
OBSERVED = "(area - curve.curve_intercept) / curve.curve_slope"

# Sheet order: left column LQC-1..HQC-3, then right column LQC-4..HQC-6.
SHEET = [
    ("LQC-1", 200535, 3.19, 89.21), ("MQC-1", 2922913, 53.80, 100.25), ("HQC-1", 5780363, 106.91, 99.62),
    ("LQC-2", 200058, 3.18, 88.96), ("MQC-2", 2920429, 53.75, 100.17), ("HQC-2", 5780508, 106.91, 99.62),
    ("LQC-3", 199288, 3.17, 88.56), ("MQC-3", 2915187, 53.65, 99.98), ("HQC-3", 5769025, 106.70, 99.42),
    ("LQC-4", 200666, 3.19, 89.28), ("MQC-4", 2920092, 53.74, 100.15), ("HQC-4", 5781894, 106.94, 99.64),
    ("LQC-5", 200214, 3.19, 89.04), ("MQC-5", 2920520, 53.75, 100.17), ("HQC-5", 5773134, 106.78, 99.49),
    ("LQC-6", 200058, 3.18, 88.96), ("MQC-6", 2920429, 53.75, 100.17), ("HQC-6", 5780508, 106.91, 99.62),
]
SHEET_THEO = {"L": 3.58, "M": 53.66, "H": 107.32}


def grp(defn: dict, key: str) -> dict:
    return next(g for g in defn["groups"] if g["key"] == key)


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    rec = grp(new, "qc_recovery")
    assert any(f["key"] == "l_area" for f in rec["fields"]), "already applied"
    keep = {f["key"]: f for f in rec["fields"] if f["key"] in ("qc_level", "theo_raw")}

    rec["fields"] = [
        keep["qc_level"],
        keep["theo_raw"],
        {"key": "solution", "kind": "input", "type": "text", "label": "Bracketing Standard Solution"},
        {"key": "theoretical_ppm", "kind": "calculated", "label": "Theoretical concentration",
         "unit": "ppm", "expression": "theo_raw", "rounding": ROUND2},
        {"key": "area", "kind": "area", "label": "Area Response", "unit": "µV·s"},
        {"key": "observed_ppm", "kind": "calculated", "label": "Observed concentration",
         "unit": "ppm", "expression": OBSERVED, "rounding": ROUND2},
        {"key": "recovery_pct", "kind": "calculated", "label": "% Recovery", "unit": "%",
         "expression": f"{OBSERVED} / theo_raw * 100", "rounding": ROUND2},
    ]
    rec["rows"] = {
        "min": 1, "max": 30, "default": 18, "labelFrom": "solution",
        "seed": [{"solution": s[0]} for s in SHEET],
    }

    for c in new["criteria"]:
        if c["key"] == "qc_recovery_low":
            c["target"] = "min(qc_recovery.recovery_pct)"
        elif c["key"] == "qc_recovery_high":
            c["target"] = "max(qc_recovery.recovery_pct)"
    return new


def convert_rows(old: list[dict]) -> list[dict]:
    left = [{"solution": r.get("l_solution"), "area": r.get("l_area")} for r in old]
    right = [{"solution": r.get("r_solution"), "area": r.get("r_area")} for r in old]
    return [{k: v for k, v in r.items() if v is not None} for r in left + right]


def check(definition: dict) -> None:
    parsed = TemplateDefinition.parse(definition)
    ev = WorksheetEvaluator(parsed)
    assert ev.evaluate({}, {}).has_blocking_failure is False
    assert parsed.result_ref == "flux.mean_flux"

    lin = [dict(r) for r in grp(definition, "linearity")["rows"]["seed"]]
    for r, a in zip(lin, [200754, 974514, 2922207, 5786622, 7842177, 11507227]):
        r["area"] = a
    qc = [dict(r) for r in grp(definition, "linearity_qc")["rows"]["seed"]]
    rows = [{"solution": s[0], "area": s[1]} for s in SHEET]
    res = ev.evaluate({}, {"linearity": lin, "linearity_qc": qc, "qc_recovery": rows})

    bad = []
    for i, (name, _, obs, recv) in enumerate(SHEET):
        got = tuple(res.row_value("qc_recovery", i, k) for k in ("theoretical_ppm", "observed_ppm", "recovery_pct"))
        if got != (SHEET_THEO[name[0]], obs, recv):
            bad.append((name, got))
    assert not bad, bad
    print("all 18 injections match the sheet (theoretical, observed, % recovery)")

    crit = {c.key: c for c in res.criteria}
    print("QC limits: lowest", crit["qc_recovery_low"].observed, crit["qc_recovery_low"].passed,
          "| highest", crit["qc_recovery_high"].observed, crit["qc_recovery_high"].passed)
    assert crit["qc_recovery_low"].observed == 88.56 and crit["qc_recovery_high"].observed == 100.25

    #  An added 19th row continues the cycle as LQC.
    res19 = ev.evaluate({}, {"linearity": lin, "linearity_qc": qc,
                             "qc_recovery": rows + [{"solution": "LQC-7", "area": 200535}]})
    assert res19.row_value("qc_recovery", 18, "theoretical_ppm") == 3.58
    print("added row 19 is treated as LQC: OK")


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

    migrations = []
    for wid, gv_raw in db.execute(
        "select id, group_values from test_worksheets where template_id=?", (tid,)
    ).fetchall():
        gv = json.loads(gv_raw) if gv_raw else {}
        old = gv.get("qc_recovery")
        if old and any("l_solution" in r or "l_area" in r or "r_area" in r for r in old):
            gv["qc_recovery"] = convert_rows(old)
            migrations.append((wid, gv))
            print(f"worksheet {wid}: {len(old)} paired rows -> {len(gv['qc_recovery'])} rows")

    if args.validate_only:
        print("--validate-only: no DB write")
        return
    db.execute("update test_templates set definition=? where id=?", (json.dumps(new), tid))
    for wid, gv in migrations:
        db.execute("update test_worksheets set group_values=? where id=?", (json.dumps(gv), wid))
    db.commit()
    back = json.loads(db.execute("select definition from test_templates where id=?", (tid,)).fetchone()[0])
    assert back == new
    assert db.execute("select status from test_templates where id=?", (tid,)).fetchone()[0] == status
    print("written and re-read byte-equal; status:", status)


if __name__ == "__main__":
    main()
