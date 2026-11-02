"""One-off: add a "Calibration curve for LQC-MQC-HQC" table to TPL-A6D-0002.

Inserts, immediately after the `linearity` group:
  * `linearity_qc_title`  - editable free-text title singleton (informational only)
  * `linearity_qc`        - 8-column input-only sequence table, add/delete rows,
                            seeded with LQC / MQC / HQC

Reads the live definition from lims.db, deep-copies, mutates, validates with the
service's two-pass gate (TemplateDefinition.parse + WorksheetEvaluator.evaluate),
then writes ONLY the `definition` column (status / approvals untouched) and
re-reads it to confirm. Take a lims.db backup before running without
--validate-only.

    python _apply_a6d_qc_table.py --validate-only
    python _apply_a6d_qc_table.py
"""
import argparse
import copy
import json
import sqlite3

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

DB = r"d:\RD-instance\GIT\backend-v2\lims.db"
CODE = "TPL-A6D-0002"
TITLE = "Calibration curve for LQC-MQC-HQC"

_FIELDS = [
    {"key": "calibration_curve", "kind": "input", "type": "text", "label": "Calibration curve"},
    {"key": "concentration_pct", "kind": "input", "type": "number", "label": "Concentration", "unit": "%"},
    {"key": "std_weight_mg", "kind": "input", "type": "number", "label": "Standard Weight", "unit": "mg"},
    {"key": "diluted_to_ml_1", "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL"},
    {"key": "ml_a", "kind": "input", "type": "number", "label": "mL", "unit": "mL"},
    {"key": "ml_b", "kind": "input", "type": "number", "label": "mL", "unit": "mL"},
    {"key": "ml_taken", "kind": "input", "type": "number", "label": "mL taken", "unit": "mL"},
    {"key": "diluted_to_ml_2", "kind": "input", "type": "number", "label": "Diluted to", "unit": "mL"},
]

# (curve, conc %, std wt, dil1, mL a, mL b, mL taken, dil2)
_SEED = [
    ("LQC", 1, 89.73, 50, 5, 50, 1, 50),
    ("MQC", 15, 89.73, 50, 5, 50, 15, 50),
    ("HQC", 30, 89.73, 50, 1, 1, 3, 50),
]


def build_groups() -> tuple[dict, dict]:
    keys = [f["key"] for f in _FIELDS]
    seed = [dict(zip(keys, row)) for row in _SEED]
    title = {
        "key": "linearity_qc_title",
        "kind": "singleton",
        "label": TITLE,
        "fields": [
            {"key": "title", "kind": "input", "type": "text", "label": "Title", "default": TITLE}
        ],
    }
    table = {
        "key": "linearity_qc",
        "kind": "sequence",
        "label": TITLE,
        # min 1 keeps one row on screen; users can add up to 15 and delete down to 1.
        "rows": {"min": 1, "max": 15, "default": 3, "labelFrom": "calibration_curve", "seed": seed},
        "fields": copy.deepcopy(_FIELDS),
    }
    return title, table


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    groups = new["groups"]
    existing = [g["key"] for g in groups]
    assert "linearity" in existing, "linearity group missing"
    assert "linearity_qc" not in existing, "already applied"
    title, table = build_groups()
    idx = existing.index("linearity") + 1
    groups[idx:idx] = [title, table]
    return new


def validate(definition: dict) -> None:
    parsed = TemplateDefinition.parse(definition)
    result = WorksheetEvaluator(parsed).evaluate({}, {})
    assert result.has_blocking_failure is False, "blank evaluate reported a blocking failure"
    assert parsed.result_ref == "flux.mean_flux", f"resultRef changed: {parsed.result_ref}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    db = sqlite3.connect(DB)
    row = db.execute(
        "select id, status, definition from test_templates where code=?", (CODE,)
    ).fetchone()
    tid, status, raw = row
    original = json.loads(raw)
    new = mutate(original)
    validate(new)
    print("order after:", [g["key"] for g in new["groups"]])
    print(f"validation OK (status stays {status!r})")

    if args.validate_only:
        print("--validate-only: no DB write")
        return

    db.execute("update test_templates set definition=? where id=?", (json.dumps(new), tid))
    db.commit()

    back = json.loads(db.execute("select definition from test_templates where id=?", (tid,)).fetchone()[0])
    assert back == new, "re-read differs from what was written"
    after_status = db.execute("select status from test_templates where id=?", (tid,)).fetchone()[0]
    assert after_status == status, "status changed"
    print("written and re-read byte-equal; status:", after_status)
    db.close()


if __name__ == "__main__":
    main()
