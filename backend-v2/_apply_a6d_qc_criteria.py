"""One-off: point the QC recovery limits (85-115 %) at the % Recovery table (TPL-A6D-0002).

qc_recovery_low / qc_recovery_high now take the min / max over both halves of
`qc_recovery` (all bracketing injections) instead of the LQC/MQC/HQC rows of
the linearity table. Limits and severity are unchanged.

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
BOTH = "qc_recovery.l_recovery_pct, qc_recovery.r_recovery_pct"
TARGETS = {"qc_recovery_low": f"min({BOTH})", "qc_recovery_high": f"max({BOTH})"}

AREAS = [(200535, 200666), (2922913, 2920092), (5780363, 5781894),
         (200058, 200214), (2920429, 2920520), (5780508, 5773134),
         (199288, 200058), (2915187, 2920429), (5769025, 5780508)]


def grp(defn: dict, key: str) -> dict:
    return next(g for g in defn["groups"] if g["key"] == key)


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    seen = set()
    for c in new["criteria"]:
        if c["key"] in TARGETS:
            c["target"] = TARGETS[c["key"]]
            seen.add(c["key"])
    assert seen == set(TARGETS), seen
    return new


def check(definition: dict) -> None:
    parsed = TemplateDefinition.parse(definition)
    ev = WorksheetEvaluator(parsed)
    assert ev.evaluate({}, {}).has_blocking_failure is False

    lin = [dict(r) for r in grp(definition, "linearity")["rows"]["seed"]]
    for r, a in zip(lin, [200754, 974514, 2922207, 5786622, 7842177, 11507227]):
        r["area"] = a
    qc = [dict(r) for r in grp(definition, "linearity_qc")["rows"]["seed"]]

    def run(areas):
        rec = [{"l_area": l, "r_area": r} for l, r in areas]
        res = ev.evaluate({}, {"linearity": lin, "linearity_qc": qc, "qc_recovery": rec})
        return {c.key: c for c in res.criteria}

    crit = run(AREAS)
    low, high = crit["qc_recovery_low"], crit["qc_recovery_high"]
    print("sheet data: lowest", low.observed, "passed", low.passed,
          "| highest", high.observed, "passed", high.passed)
    assert round(float(low.observed), 2) == 88.56 and low.passed is True, low
    assert round(float(high.observed), 2) == 100.25 and high.passed is True, high

    #  An LQC injection at ~80 % recovery must now trip the low limit.
    bad = list(AREAS)
    bad[0] = (int(0.80 * 3.57735564 * 53797.61 + 28844.9), bad[0][1])
    low_bad = run(bad)["qc_recovery_low"]
    print("one injection at ~80 %: lowest", low_bad.observed, "passed", low_bad.passed)
    assert low_bad.passed is False

    #  Blank worksheet: not yet assessable, not a failure.
    blank = {c.key: c for c in ev.evaluate({}, {}).criteria}
    assert blank["qc_recovery_low"].passed is None
    print("blank worksheet: not yet assessable (passed=None): OK")


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
