"""One-off: replace TPL-A3-0001's Saturated Solution Preparations with Media Solutions.

The earlier TPL-A3 media-table migration made `std_areas` a 1..10 dynamic
media-column table. This follow-up replaces the old single `samples` section
with a complete solution block for every active media column:

* `media_solution_N` — a visible singleton card titled from
  `media_names.media_N` (falling back to "Media N"), with one Solution Dilution
  row: Pipette 1 / Dilution 1 / Pipette 2 / Dilution 2 / Pipette 3 / Dilution 3.
* `media_sets_N` — the hidden data table rendered inside that card: SET 1..5 by
  default (add/delete 1..10), Area 1, Area 2, Mean Area, and mg/mL, then a
  Mean mg/mL footer. The calculated `mg_ml_raw` preserves formula precision;
  the displayed mg/mL and footer round only for presentation.
* N is visible only while `media_names.media_count >= N`, so the number of
  cards always mirrors Standard Area in Media. `std_areas.columnSet.linkedGroups`
  pairs each media column with its parent/card and Set table. The frontend moves
  these paired values with a media column on delete and resets a fresh pair on
  add, avoiding detached media data.

Formula parity with `Test types/Saturation solubility by HPLC.xlsx`:
  mg/mL = Mean Area / STD mean for this media * standard.conc_ppm
          * (Dilution3/Pipette3) * (Dilution2/Pipette2)
          * (Dilution1/Pipette1) / 1000

The template's former `samples` group and `prep_agreement` criterion are
removed. `resultRef` becomes the first active medium's Mean mg/mL
(`media_solution_1.mean_mg_ml`), carrying forward the first-media reference
choice made for this worksheet.

Existing worksheet 53 has only blank/default old sample rows. This migration
removes that obsolete group and preserves all other stored groups. It ABORTS if
an old sample row now holds a real prep, area, or non-default dilution value.

Writes the template and all bound worksheet group-values in one optimistic,
transactional update. A timestamped `lims.db.bak-a3media-solutions-*` backup is
created before any write. Run with --validate-only first.
"""
import argparse
import copy
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.expression import EMPTY
from src.domain.services.calculation.template_schema import TemplateDefinition

DB = Path(r"d:\RD-instance\GIT\backend-v2\lims.db")
CODE = "TPL-A3-0001"
VERSION = 1
MAX_MEDIA = 10
DEFAULT_MEDIA = 6
MAX_SET_ROWS = 10
DEFAULT_SET_ROWS = 5
MEDIA = range(1, MAX_MEDIA + 1)
COUNT_REF = "media_names.media_count"

#  Paper-sheet defaults from rows 30 / 40 / 50 / 60 / 70 / 80.
DILUTIONS = {
    1: (0.5, 10, 0.8, 25, 1, 1),
    2: (0.5, 10, 0.8, 50, 1, 1),
    3: (0.5, 10, 1, 50, 1, 1),
    4: (5, 25, 1, 1, 1, 1),
    5: (5, 25, 1, 1, 1, 1),
    6: (5, 25, 1, 1, 1, 1),
    #  Added media columns start from a neutral, editable 1:1 dilution.
    7: (1, 1, 1, 1, 1, 1),
    8: (1, 1, 1, 1, 1, 1),
    9: (1, 1, 1, 1, 1, 1),
    10: (1, 1, 1, 1, 1, 1),
}

SHEET_STD = [1264265, 1266600, 1267571, 1267739, 1266671, None]


def _solution_key(n: int) -> str:
    return f"media_solution_{n}"


def _sets_key(n: int) -> str:
    return f"media_sets_{n}"


def _solution_group(n: int) -> dict:
    p1, d1, p2, d2, p3, d3 = DILUTIONS[n]
    key = _solution_key(n)
    sets = _sets_key(n)
    return {
        "key": key,
        "kind": "singleton",
        "label": f"Media {n}",
        # UI-only: the card title follows the editable Standard Area header.
        "labelFrom": f"media_names.media_{n}[0]",
        "showIf": f"{COUNT_REF}[0] >= {n}",
        # UI-only: render this singleton and its hidden source table as one card.
        "solutionBlock": {"setsGroup": sets, "dilutionLabel": "Solution Dilution"},
        "fields": [
            {"key": "pipette_1", "kind": "input", "label": "Pipette 1", "unit": "mL", "default": p1},
            {"key": "dilution_1", "kind": "input", "label": "Dilution 1", "unit": "mL", "default": d1},
            {"key": "pipette_2", "kind": "input", "label": "Pipette 2", "unit": "mL", "default": p2},
            {"key": "dilution_2", "kind": "input", "label": "Dilution 2", "unit": "mL", "default": d2},
            {"key": "pipette_3", "kind": "input", "label": "Pipette 3", "unit": "mL", "default": p3},
            {"key": "dilution_3", "kind": "input", "label": "Dilution 3", "unit": "mL", "default": d3},
            {
                "key": "mean_mg_ml",
                "kind": "calculated",
                "label": "Mean mg/mL",
                "unit": "mg/mL",
                "hidden": True,
                "expression": f"mean({sets}.mg_ml_raw)",
                "rounding": {"mode": "round", "digits": 4},
            },
        ],
    }


def _sets_group(n: int) -> dict:
    solution = _solution_key(n)
    return {
        "key": _sets_key(n),
        "kind": "table",
        "label": f"Media {n} Sets",
        # This normal table is rendered inside media_solution_N's visible card.
        "hidden": True,
        "rows": {"min": 1, "max": MAX_SET_ROWS, "default": DEFAULT_SET_ROWS},
        "rowLabel": {"header": "", "format": "SET {n}"},
        "fields": [
            {"key": "area_1", "kind": "area", "label": "Area 1"},
            {"key": "area_2", "kind": "area", "label": "Area 2"},
            {
                "key": "mean_area",
                "kind": "calculated",
                "label": "Mean Area",
                "expression": "mean(area_1, area_2)",
            },
            {
                "key": "mg_ml_raw",
                "kind": "calculated",
                "label": "mg/mL raw",
                "hidden": True,
                "expression": (
                    f"mean_area / stats.mean_m{n} * standard.conc_ppm * "
                    f"{solution}.dilution_3 / {solution}.pipette_3 * "
                    f"{solution}.dilution_2 / {solution}.pipette_2 * "
                    f"{solution}.dilution_1 / {solution}.pipette_1 / 1000"
                ),
            },
            {
                "key": "mg_ml",
                "kind": "calculated",
                "label": "mg/mL",
                "unit": "mg/mL",
                "expression": "mg_ml_raw",
                "rounding": {"mode": "round", "digits": 4},
            },
        ],
        "footer": [
            {
                "label": "Mean mg/mL",
                "ref": f"{solution}.mean_mg_ml",
                "unit": "mg/mL",
                "rounding": {"mode": "round", "digits": 4},
            }
        ],
    }


def _default_std_rows() -> list[dict]:
    return [{f"media_{n}": None for n in MEDIA} for _ in range(DEFAULT_MEDIA)]


def _standard_rows() -> list[dict]:
    return [
        {f"media_{n}": SHEET_STD[row] for n in range(1, DEFAULT_MEDIA + 1)}
        for row in range(len(SHEET_STD))
    ]


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    by = {group["key"]: group for group in new["groups"]}
    assert "samples" in by, "samples already removed"
    assert "media_solution_1" not in by, "media solutions already applied"
    assert by["std_areas"]["label"] == "Standard Area in Media"
    assert by["stats"].get("hidden") is True

    column_set = by["std_areas"].get("columnSet")
    assert column_set and column_set["columns"] == [f"media_{n}" for n in MEDIA]
    assert not column_set.get("linkedGroups"), "linked groups already configured"
    column_set["linkedGroups"] = [
        [_solution_key(n), _sets_key(n)] for n in MEDIA
    ]

    solution_groups = []
    for n in MEDIA:
        solution_groups.extend([_solution_group(n), _sets_group(n)])

    groups = []
    for group in new["groups"]:
        if group["key"] == "samples":
            continue
        if group["key"] == "stats":
            groups.extend(solution_groups)
        groups.append(group)
    new["groups"] = groups

    assert new["resultRef"] == "samples.mean_solubility", new["resultRef"]
    new["resultRef"] = "media_solution_1.mean_mg_ml"

    old_criteria = new["criteria"]
    assert any(c["key"] == "prep_agreement" for c in old_criteria)
    new["criteria"] = [c for c in old_criteria if c["key"] != "prep_agreement"]
    assert len(new["criteria"]) == len(old_criteria) - 1
    return new


def _old_samples_are_safe_to_remove(rows: list[dict]) -> bool:
    """Only the old blank/default sample rows may be removed automatically."""
    known = {"prep_ref", "time_point", "aliquot_ml", "diluted_to_ml", "area"}
    for row in rows:
        row = row or {}
        if row.get("prep_ref") not in (None, ""):
            return False
        if row.get("time_point") not in (None, ""):
            return False
        if row.get("area") not in (None, ""):
            return False
        if row.get("aliquot_ml") not in (None, "", 1, 1.0):
            return False
        if row.get("diluted_to_ml") not in (None, "", 1, 1.0):
            return False
        if any(key not in known and value not in (None, "") for key, value in row.items()):
            return False
    return True


def migrate_worksheet(group_values: dict) -> dict:
    """Remove only blank/default legacy samples; preserve all retained groups."""
    gv = copy.deepcopy(group_values or {})
    old_samples = gv.get("samples") or []
    if not _old_samples_are_safe_to_remove(old_samples):
        raise SystemExit(
            "ABORT: worksheet has meaningful Saturated Solution Preparations data; "
            "reconcile it before deleting the section"
        )
    gv.pop("samples", None)
    return gv


# ─────────────────────────── checks ───────────────────────────

def check(old_def: dict, new_def: dict, worksheets: list[tuple[int, dict, dict]]) -> None:
    parsed = TemplateDefinition.parse(new_def)
    evaluator = WorksheetEvaluator(parsed)

    assert parsed.result_ref == "media_solution_1.mean_mg_ml"
    assert parsed.group("samples") is None
    expected_group_keys = ["standard", "media_names", "std_areas"]
    for n in MEDIA:
        expected_group_keys.extend([_solution_key(n), _sets_key(n)])
    expected_group_keys.append("stats")
    assert [group.key for group in parsed.groups] == expected_group_keys
    for n in MEDIA:
        parent = parsed.group(_solution_key(n))
        sets = parsed.group(_sets_key(n))
        assert parent is not None and sets is not None
        assert sets.rows.default == DEFAULT_SET_ROWS and sets.rows.max == MAX_SET_ROWS
    assert len(parsed.area_field_refs) == MAX_MEDIA + MAX_MEDIA * 2
    assert all(c.key != "prep_agreement" for c in parsed.criteria)

    # An empty/new worksheet has 6 active media values, 5 blank Set rows per
    # provisioned group, and no blocking suitability failure.
    empty = evaluator.evaluate({}, {})
    assert empty.has_blocking_failure is False
    assert len(empty.rows[_sets_key(1)]) == DEFAULT_SET_ROWS
    assert empty.reportable_result is EMPTY

    # Source-sheet Media 1: 780639 / 1266569.2 * standard chain * 625 = 68.777341...
    groups = {
        "standard": [{
            "weight_mg": 32.17, "vol_1": 50, "pip_1": 6, "vol_2": 20,
            "pip_2": 1, "vol_3": 1, "potency": 92.5,
        }],
        "media_names": [{"media_count": DEFAULT_MEDIA}],
        "std_areas": _standard_rows(),
        _sets_key(1): [{"area_1": 782140, "area_2": 779138}],
        _sets_key(2): [{"area_1": 234947, "area_2": 231538}],
        _sets_key(3): [{"area_1": 241767, "area_2": 250110}],
    }
    result = evaluator.evaluate({}, groups)
    assert result.row_value(_sets_key(1), 0, "mean_area") == 780639.0
    assert result.row_value(_sets_key(1), 0, "mg_ml") == 68.7773
    assert result.values["media_solution_1.mean_mg_ml"] == 68.7773
    assert result.reportable_result == 68.7773
    assert result.row_value(_sets_key(2), 0, "mg_ml") == 41.0991
    assert result.values["media_solution_2.mean_mg_ml"] == 41.0991
    assert result.row_value(_sets_key(3), 0, "mg_ml") == 34.669
    print("sheet parity: Media 1=68.7773, Media 2=41.0991, Media 3=34.6690 mg/mL")

    # Every media uses its own matching standard mean: give Media 2 a different
    # mean and show that only Media 2's result changes.
    shifted = copy.deepcopy(groups)
    for row in shifted["std_areas"]:
        row["media_2"] = 2_000_000 if row["media_2"] is not None else None
    result2 = evaluator.evaluate({}, shifted)
    assert result2.row_value(_sets_key(1), 0, "mg_ml") == 68.7773
    assert result2.row_value(_sets_key(2), 0, "mg_ml") != 41.0991
    print("per-media standard means are independent: Media 2 result changed only in Media 2")

    # Existing worksheets retain all non-sample data and evaluate with the new shape.
    for ws_id, before, after in worksheets:
        assert "samples" not in after
        for key in before:
            if key != "samples":
                assert after[key] == before[key], (ws_id, key)
        migrated = evaluator.evaluate({}, after)
        assert len(migrated.rows[_sets_key(1)]) == DEFAULT_SET_ROWS
        print(f"worksheet {ws_id}: removed only blank/default samples; retained", sorted(after))


def backup(db: sqlite3.Connection) -> Path:
    target = DB.with_name(f"{DB.name}.bak-a3media-solutions-{datetime.now():%Y%m%d-%H%M%S}")
    target_db = sqlite3.connect(target)
    with target_db:
        db.backup(target_db)
    target_db.close()
    assert target.stat().st_size > 0
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    db = sqlite3.connect(DB)
    row = db.execute(
        "select id, status, definition from test_templates where code=? and version=?",
        (CODE, VERSION),
    ).fetchone()
    assert row is not None, f"{CODE} v{VERSION} not found"
    template_id, status, raw_definition = row
    old = json.loads(raw_definition)
    new = mutate(old)

    worksheets: list[tuple[int, str, dict, dict]] = []
    for worksheet_id, raw_values in db.execute(
        "select id, group_values from test_worksheets where template_id=?", (template_id,)
    ).fetchall():
        original_values = raw_values or "{}"
        before = json.loads(original_values)
        worksheets.append((worksheet_id, original_values, before, migrate_worksheet(before)))

    check(old, new, [(worksheet_id, before, after) for worksheet_id, _raw, before, after in worksheets])
    if args.validate_only:
        print("--validate-only: no DB write")
        return

    print("backup:", backup(db))
    with db:
        # Compare original JSON inside both UPDATEs so a concurrent analyst save
        # or definition edit stops this migration instead of being overwritten.
        changed = db.execute(
            "update test_templates set definition=? where id=? and version=? and definition=?",
            (json.dumps(new), template_id, VERSION, raw_definition),
        )
        assert changed.rowcount == 1, "template changed while preparing migration"
        for worksheet_id, original_values, _before, after in worksheets:
            changed = db.execute(
                "update test_worksheets set group_values=? where id=? and group_values=?",
                (json.dumps(after), worksheet_id, original_values),
            )
            assert changed.rowcount == 1, f"worksheet {worksheet_id} changed while preparing migration"

    stored_def = json.loads(db.execute("select definition from test_templates where id=?", (template_id,)).fetchone()[0])
    assert stored_def == new
    assert db.execute("select status from test_templates where id=?", (template_id,)).fetchone()[0] == status
    for worksheet_id, _original_values, _before, after in worksheets:
        stored_values = json.loads(db.execute("select group_values from test_worksheets where id=?", (worksheet_id,)).fetchone()[0])
        assert stored_values == after
    print("written and re-read equal; template status:", status, "; worksheets:", [item[0] for item in worksheets])


if __name__ == "__main__":
    main()
