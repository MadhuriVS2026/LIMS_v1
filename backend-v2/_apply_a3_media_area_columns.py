"""One-off: add dynamic Area columns to every TPL-A3-0001 Media Solution Set table.

Each `media_sets_N` table currently has fixed Area 1 / Area 2 columns. This
migration provisions Area 1..10, shows the first two by default, and enables
the existing generic column-set UI in each Media Solution card:

* Add Column: reveals the next Area column (Area 3 ... Area 10).
* Edit: the visible Area cells remain editable through the media card's normal
  Edit/Save controls.
* Delete Column: any active Area column can be deleted while more than one
  remains; later Area values shift left and Mean Area / mg/mL recalculate.

A hidden `media_solution_N.area_count` input records the number of active Area
columns (default 2). It is seeded for all ten Media Solution singleton groups,
so fresh worksheets and print views both show Area 1 + Area 2 without relying
on transient browser state. `mean_area` aggregates all ten provisioned fields;
blank/inactive fields are skipped by the calculation engine.

No values are discarded. Existing Area 1/Area 2 values stay in place; newly
provisioned Area 3..Area 10 cells begin blank. Writes are optimistic and
transactional, after a `lims.db.bak-a3media-areas-*` SQLite backup. Run with
--validate-only first.
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
MAX_AREAS = 10
DEFAULT_AREAS = 2
MEDIA = range(1, MAX_MEDIA + 1)
AREAS = range(1, MAX_AREAS + 1)


def _solution_key(n: int) -> str:
    return f"media_solution_{n}"


def _sets_key(n: int) -> str:
    return f"media_sets_{n}"


def _area_keys() -> list[str]:
    return [f"area_{n}" for n in AREAS]


def _mean_expression() -> str:
    return "mean(" + ", ".join(_area_keys()) + ")"


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    by = {group["key"]: group for group in new["groups"]}
    assert by["std_areas"]["label"] == "Standard Area in Media"
    assert "samples" not in by, "Media Solutions migration must be applied first"

    for media in MEDIA:
        parent = by[_solution_key(media)]
        sets = by[_sets_key(media)]
        parent_fields = parent["fields"]
        assert not any(field["key"] == "area_count" for field in parent_fields), "already applied"
        parent_mean_index = next(
            index for index, field in enumerate(parent_fields) if field["key"] == "mean_mg_ml"
        )
        parent_fields.insert(parent_mean_index, {
            "key": "area_count",
            "kind": "input",
            "label": "Area columns in use",
            "default": DEFAULT_AREAS,
            "hidden": True,
        })
        # Seed the count when any future worksheet is created. The field default
        # still protects direct evaluator/preview use without stored values.
        parent["rows"] = {"seed": [{"area_count": DEFAULT_AREAS}]}

        old_fields = {field["key"]: field for field in sets["fields"]}
        assert [field["key"] for field in sets["fields"]] == [
            "area_1", "area_2", "mean_area", "mg_ml_raw", "mg_ml"
        ], sets["fields"]
        area_fields = []
        for n in AREAS:
            if n <= 2:
                field = copy.deepcopy(old_fields[f"area_{n}"])
            else:
                field = {"key": f"area_{n}", "kind": "area", "label": f"Area {n}"}
            if n > 1:
                field["showIf"] = f"{_solution_key(media)}.area_count[0] >= {n}"
            area_fields.append(field)

        mean_area = copy.deepcopy(old_fields["mean_area"])
        mean_area["expression"] = _mean_expression()
        sets["fields"] = [
            *area_fields,
            mean_area,
            copy.deepcopy(old_fields["mg_ml_raw"]),
            copy.deepcopy(old_fields["mg_ml"]),
        ]
        sets["columnSet"] = {
            "columns": _area_keys(),
            "countRef": f"{_solution_key(media)}.area_count",
            "min": 1,
        }
    return new


def migrate_worksheet(group_values: dict) -> dict:
    """Add each parent group's persisted Area count without touching Area data."""
    values = copy.deepcopy(group_values or {})
    for media in MEDIA:
        key = _solution_key(media)
        rows = values.get(key)
        if rows:
            rows[0].setdefault("area_count", DEFAULT_AREAS)
        else:
            values[key] = [{"area_count": DEFAULT_AREAS}]
    return values


# ─────────────────────────── checks ───────────────────────────

def _standard_inputs() -> dict:
    return {
        "standard": [{
            "weight_mg": 32.17, "vol_1": 50, "pip_1": 6, "vol_2": 20,
            "pip_2": 1, "vol_3": 1, "potency": 92.5,
        }],
        "media_names": [{"media_count": 6}],
        "std_areas": [
            {f"media_{n}": area for n in range(1, 7)}
            for area in (1264265, 1266600, 1267571, 1267739, 1266671, None)
        ],
    }


def check(old_def: dict, new_def: dict, worksheets: list[tuple[int, dict, dict]]) -> None:
    old_evaluator = WorksheetEvaluator(TemplateDefinition.parse(old_def))
    parsed = TemplateDefinition.parse(new_def)
    evaluator = WorksheetEvaluator(parsed)

    assert parsed.result_ref == "media_solution_1.mean_mg_ml"
    for media in MEDIA:
        parent = parsed.group(_solution_key(media))
        sets = parsed.group(_sets_key(media))
        assert parent is not None and sets is not None
        assert parent.rows.seed == ({"area_count": DEFAULT_AREAS},)
        assert [field.key for field in sets.fields] == [
            *_area_keys(), "mean_area", "mg_ml_raw", "mg_ml"
        ]
    assert len(parsed.area_field_refs) == MAX_MEDIA + MAX_MEDIA * MAX_AREAS

    # Existing two-area method parity: Media 1's source-sheet result is unchanged.
    common = {
        **_standard_inputs(),
        _sets_key(1): [{"area_1": 782140, "area_2": 779138}],
    }
    old_result = old_evaluator.evaluate({}, common)
    new_result = evaluator.evaluate({}, {
        **common,
        _solution_key(1): [{"area_count": 2}],
    })
    assert old_result.row_value(_sets_key(1), 0, "mean_area") == new_result.row_value(_sets_key(1), 0, "mean_area") == 780639.0
    assert old_result.row_value(_sets_key(1), 0, "mg_ml") == new_result.row_value(_sets_key(1), 0, "mg_ml") == 68.7773

    # A third Area joins the exact same mean and result calculation when added.
    with_third = evaluator.evaluate({}, {
        **common,
        _solution_key(1): [{"area_count": 3}],
        _sets_key(1): [{"area_1": 10, "area_2": 20, "area_3": 30}],
    })
    assert with_third.row_value(_sets_key(1), 0, "mean_area") == 20.0
    assert with_third.row_value(_sets_key(1), 0, "mg_ml") is not EMPTY
    assert all(with_third.row_value(_sets_key(1), 0, f"area_{n}") is EMPTY for n in range(4, 11))
    print("Area 1/2 parity: 68.7773 mg/mL; Area 3 joins Mean Area: (10+20+30)/3 = 20")

    # Stored worksheet data is retained. The migration only adds each parent
    # counter, and Mean Area over Area 1/2 plus blank new columns is exactly the
    # same calculation as the current two-Area definition.
    for worksheet_id, before, after in worksheets:
        for key, value in before.items():
            if key.startswith("media_solution_"):
                continue
            assert after[key] == value, (worksheet_id, key)
        for media in MEDIA:
            key = _solution_key(media)
            before_row = (before.get(key) or [{}])[0]
            after_row = after[key][0]
            for field, value in before_row.items():
                assert after_row[field] == value, (worksheet_id, key, field)
            assert after_row["area_count"] == before_row.get("area_count", DEFAULT_AREAS)
        old_worksheet_result = old_evaluator.evaluate({}, before)
        new_worksheet_result = evaluator.evaluate({}, after)
        assert new_worksheet_result.reportable_result == old_worksheet_result.reportable_result
        print(
            f"worksheet {worksheet_id}: retained values; added 10 default Area counters; "
            f"reportable remains {new_worksheet_result.reportable_result}"
        )


def backup(db: sqlite3.Connection) -> Path:
    target = DB.with_name(f"{DB.name}.bak-a3media-areas-{datetime.now():%Y%m%d-%H%M%S}")
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

    assert json.loads(db.execute("select definition from test_templates where id=?", (template_id,)).fetchone()[0]) == new
    assert db.execute("select status from test_templates where id=?", (template_id,)).fetchone()[0] == status
    for worksheet_id, _original_values, _before, after in worksheets:
        stored = json.loads(db.execute("select group_values from test_worksheets where id=?", (worksheet_id,)).fetchone()[0])
        assert stored == after
    print("written and re-read equal; template status:", status, "; worksheets:", [item[0] for item in worksheets])


if __name__ == "__main__":
    main()
