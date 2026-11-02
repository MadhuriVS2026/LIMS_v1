"""Replace TPL-A4-0003 Sample Preparation with the supplied Sample details table.

The replacement appears immediately below Standard Preparations and retains the
source worksheet's storage, L.C., average weight, sample weight, and dilution
inputs. Both impurity calculation tables are rewired to those exact fields.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

DB = Path("lims.db")
CODE = "TPL-A4-0003"
VERSION = 1
ACTOR = "kiro-a4sampledetails"

SAMPLE_ROW = {
    "storage_condition": "25°C/60%RH_9M_Without Secondory Carton",
    "lc_mg": 1.0,
    "av_wt": 1.0,
    "sample_weight": 60.41,
    "vf_1": 100,
    "dilution": 1,
    "vf_2": 1,
}


def sample_details_table_group() -> dict[str, Any]:
    return {
        "key": "sample_details_table",
        "kind": "table",
        "label": "Sample details",
        "showRowNumbers": False,
        "rows": {"min": 1, "max": 1, "default": 1, "seed": [dict(SAMPLE_ROW)]},
        "fields": [
            {
                "key": "storage_condition",
                "kind": "input",
                "type": "text",
                "label": "Storage pack/ condition",
                "width": "43%",
            },
            {
                "key": "lc_mg",
                "kind": "input",
                "label": "L.C. (mg)",
                "rounding": {"mode": "round", "digits": 3},
                "width": "8%",
            },
            {
                "key": "av_wt",
                "kind": "input",
                "label": "Av. Wt. (mg)",
                "rounding": {"mode": "round", "digits": 2},
                "width": "10%",
            },
            {
                "key": "sample_weight",
                "kind": "input",
                "label": "SPL in (mg)",
                "rounding": {"mode": "round", "digits": 2},
                "width": "11%",
            },
            {
                "key": "vf_1",
                "kind": "input",
                "label": "V.F1 (ml)",
                "width": "10%",
            },
            {
                "key": "dilution",
                "kind": "input",
                "label": "Dil. (ml)",
                "width": "9%",
            },
            {
                "key": "vf_2",
                "kind": "input",
                "label": "V.F2. (ml)",
                "width": "9%",
            },
        ],
    }


def pct_uncorrected_expression() -> str:
    # Matches the source-sheet chain:
    # area/std mean × standard concentration × V.F1/Dil.×V.F2×Av.Wt./L.C./SPL.
    base = (
        "area / stats.mean_std * "
        "(std_preps.weight_mg[0] / std_preps.vol_1[0] "
        "* std_preps.pip_1[0] / std_preps.vol_2[0] "
        "* std_preps.pip_2[0] / std_preps.vol_3[0]) "
        "* sample_details_table.vf_1[0] / sample_details_table.dilution[0] "
        "* sample_details_table.vf_2[0] * sample_details_table.av_wt[0] "
        "/ sample_details_table.lc_mg[0] / sample_details_table.sample_weight[0] "
        "* std_preps.potency[0] / 100 "
        "* std_preps.mw_base[0] / std_preps.mw_salt[0] * 100"
    )
    return f"if(include_calculation, if(isblank(area), 0, {base}), blank())"


def field_by_key(group: dict[str, Any], key: str) -> dict[str, Any]:
    field = next((item for item in group.get("fields", []) if item.get("key") == key), None)
    if field is None:
        raise RuntimeError(f"{group.get('key')} is missing field {key}")
    return field


def proposed_definition(raw_definition: str) -> dict[str, Any]:
    definition = json.loads(raw_definition)
    groups = definition.get("groups") or []
    keys = {group.get("key") for group in groups}
    if "sample_prep" not in keys or "std_preps" not in keys:
        raise RuntimeError("Sample Preparation or Standard Preparations group is missing")
    if "sample_details_table" in keys:
        raise RuntimeError("Sample details group already exists")

    pct_expression = pct_uncorrected_expression()
    for key in ("impurities", "known_impurities"):
        group = next((item for item in groups if item.get("key") == key), None)
        if group is None:
            raise RuntimeError(f"{key} group is missing")
        field_by_key(group, "pct_uncorrected")["expression"] = pct_expression

    next_groups: list[dict[str, Any]] = []
    inserted = False
    for group in groups:
        if group.get("key") == "sample_prep":
            continue
        next_groups.append(group)
        if group.get("key") == "std_preps":
            next_groups.append(sample_details_table_group())
            inserted = True
    if not inserted:
        raise RuntimeError("Standard Preparations group is missing")

    definition["groups"] = next_groups
    return definition


def legacy_sample_has_entered_values(rows: Any) -> bool:
    if not isinstance(rows, list) or not rows:
        return False
    row = rows[0] if isinstance(rows[0], dict) else {}
    # Default one-values are not treated as entered values. Any weight/volume
    # not equal to the old neutral default needs a human migration decision.
    if row.get("sample_weight") not in (None, ""):
        return True
    if row.get("s_vol_1") not in (None, ""):
        return True
    for key in ("s_pip_1", "s_vol_2", "s_pip_2", "s_vol_3", "av_wt", "lc_mg"):
        value = row.get(key)
        if value not in (None, "", 1, 1.0):
            return True
    return False


def migrate_group_values(raw: str) -> dict[str, Any]:
    values = json.loads(raw or "{}")
    if "sample_details_table" in values:
        raise RuntimeError("Worksheet already has a sample_details_table group")
    if legacy_sample_has_entered_values(values.get("sample_prep")):
        raise RuntimeError("Worksheet contains entered Sample Preparation data and needs a manual migration")
    values.pop("sample_prep", None)
    values["sample_details_table"] = [dict(SAMPLE_ROW)]
    return values


def source_example_values(definition: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    groups = {group["key"]: group for group in definition["groups"]}
    context = {"rrf_mode": "RRF (multiplication factor)"}
    values = {
        "std_preps": [
            {
                "name": "Lenacapavir Na",
                "weight_mg": 30.71,
                "vol_1": 50,
                "pip_1": 1,
                "vol_2": 1,
                "pip_2": 1,
                "vol_3": 1,
                "lc_mg": 1,
                "av_wt_mg": 1,
                "mw_base": 1,
                "mw_salt": 1,
                "potency": 98.78,
            }
        ],
        "sample_details_table": [dict(SAMPLE_ROW)],
        "std_injections": [
            {"area": area}
            for area in [10715758, 10706105, 10682530, 10682530, 10689079]
        ],
        "bkt": [
            {"area": area}
            for area in [10773612, 10768957, 10794726, 10811829, 10834226, 10830705]
        ],
        "sst": [{"area_lena2_sensitivity": 4388, "area_lena2_std": 9298867, "dilution_factor": 2000}],
        "sst_criteria": [{}, {}, {}, {"result": "23.032"}],
        "impurities": [dict(row) for row in groups["impurities"]["rows"]["seed"]],
        "known_impurities": [dict(row) for row in groups["known_impurities"]["rows"]["seed"]],
    }
    return context, values


def validate_source_example(evaluator: WorksheetEvaluator, definition: dict[str, Any]) -> None:
    context, values = source_example_values(definition)
    result = evaluator.evaluate(context, values)
    unknowns = {row["name"]: row for row in result.rows["impurities"]}
    known = {row["name"]: row for row in result.rows["known_impurities"]}
    if (unknowns["Unknown-1"]["rrt"], unknowns["Unknown-1"]["pct"], unknowns["Unknown-1"]["reported"]) != (0.8, 0.0115, "BLQ"):
        raise RuntimeError("Unknown-1 source calculation mismatch")
    if (unknowns["Unknown-2"]["rrt"], unknowns["Unknown-2"]["pct"], unknowns["Unknown-2"]["reported"]) != (1.61, 0.0647, 0.065):
        raise RuntimeError("Unknown-2 source calculation mismatch")
    if (known["1) Emcure: Amine  + N-Acetyl Imp. (RRT-0.60)"]["rrt"], known["1) Emcure: Amine  + N-Acetyl Imp. (RRT-0.60)"]["pct"], known["1) Emcure: Amine  + N-Acetyl Imp. (RRT-0.60)"]["reported"]) != (0.58, 0.0144, "BLQ"):
        raise RuntimeError("Known Amine/N-Acetyl source calculation mismatch")
    expected_summary = {
        "summary.max_single_unknown": 0.0647,
        "summary.max_single_unknown_reported": 0.065,
        "summary.total_unknowns": 0.076,
        "summary.total_unknowns_reported": 0.065,
        "summary.total_knowns": 0.068,
        "summary.total_knowns_reported": 0.0,
        "summary.total_all": 0.144,
        "summary.total_all_reported": 0.065,
    }
    for key, expected in expected_summary.items():
        if result.values[key] != expected:
            raise RuntimeError(f"Source summary mismatch for {key}: {result.values[key]}")


def backup_database() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"lims.db.bak-a4sampledetails-{stamp}")
    with sqlite3.connect(DB) as source, sqlite3.connect(backup) as target:
        source.backup(target)
    return backup


def main() -> int:
    if not DB.is_file():
        print(f"ERROR: {DB} does not exist")
        return 1

    validate_only = "--validate-only" in sys.argv
    con = sqlite3.connect(DB, timeout=30)
    try:
        template = con.execute(
            "select id, code, archetype, version, status, test_id, definition "
            "from test_templates where code=? and version=? and status=?",
            (CODE, VERSION, "Active"),
        ).fetchone()
        if template is None:
            raise RuntimeError(f"Active {CODE} v{VERSION} was not found")

        template_id, code, archetype, version, status, test_id, raw_definition = template
        definition = proposed_definition(raw_definition)
        parsed = TemplateDefinition.parse(definition)
        evaluator = WorksheetEvaluator(parsed)
        validate_source_example(evaluator, definition)

        worksheets = con.execute(
            "select id, context_values, group_values from test_worksheets "
            "where template_id=? and template_version=? and status=? order by id",
            (template_id, VERSION, "InProgress"),
        ).fetchall()
        migrated_values: list[tuple[int, str, dict[str, Any]]] = []
        for worksheet_id, raw_context, raw_values in worksheets:
            values = migrate_group_values(raw_values)
            evaluator.evaluate(json.loads(raw_context or "{}"), values)
            migrated_values.append((worksheet_id, raw_values, values))

        if validate_only:
            print(f"valid={CODE} v{VERSION}; Sample details appears after Standard Preparations")
            print("source_example=Unknown-1 0.0115/BLQ; Unknown-2 0.0647/0.065; total=0.1440")
            print(f"validated_in_progress_worksheets={len(migrated_values)}")
            return 0

        backup = backup_database()
        now = datetime.now().isoformat(timespec="seconds")
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "update test_templates set definition=?, modified_by=?, modified_date=? "
            "where id=? and code=? and version=? and status=? and definition=?",
            (json.dumps(definition), ACTOR, now, template_id, CODE, VERSION, "Active", raw_definition),
        )
        if cur.rowcount != 1:
            raise RuntimeError("Template changed during update")

        for worksheet_id, raw_values, values in migrated_values:
            cur = con.execute(
                "update test_worksheets set group_values=?, modified_by=?, modified_date=? "
                "where id=? and status=? and group_values=?",
                (json.dumps(values), ACTOR, now, worksheet_id, "InProgress", raw_values),
            )
            if cur.rowcount != 1:
                raise RuntimeError(f"Worksheet {worksheet_id} changed during migration")

        identity = con.execute(
            "select id, code, archetype, version, status, test_id from test_templates where id=?",
            (template_id,),
        ).fetchone()
        expected_identity = (template_id, code, archetype, version, status, test_id)
        if identity != expected_identity:
            raise RuntimeError(f"Template identity changed: {expected_identity} -> {identity}")

        con.commit()
        print(f"backup={backup.name}")
        print(f"template={CODE} v{VERSION} id={template_id}; Sample details installed")
        print(f"migrated_in_progress_worksheets={len(migrated_values)}")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
