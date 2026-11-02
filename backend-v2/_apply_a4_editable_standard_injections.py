"""Make TPL-A4-0003 Standard Injections an editable, row-managed table.

Moves standard injection area entry out of Standard Preparations, preserving any
existing areas. The editable table then drives standard statistics, pooled BKT
statistics, and the Sensitivity STD/Inj-1 lookup.
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
ACTOR = "kiro-a4editstdinj"


def nonblank(value: Any) -> bool:
    return value is not None and value != ""


def editable_standard_group(existing: dict[str, Any]) -> dict[str, Any]:
    group = dict(existing)
    group["rows"] = {"min": 1, "max": 6, "default": 5}
    group["fields"] = [{"key": "area", "kind": "area", "label": "STD Area"}]
    return group


def field_by_key(group: dict[str, Any], key: str) -> dict[str, Any]:
    field = next((item for item in group.get("fields", []) if item.get("key") == key), None)
    if field is None:
        raise RuntimeError(f"{group.get('key')} is missing field {key}")
    return field


def proposed_definition(raw_definition: str) -> dict[str, Any]:
    definition = json.loads(raw_definition)
    groups = {group.get("key"): group for group in definition.get("groups", [])}
    std_preps = groups.get("std_preps")
    std_injections = groups.get("std_injections")
    stats = groups.get("stats")
    sst = groups.get("sst")
    if not all((std_preps, std_injections, stats, sst)):
        raise RuntimeError("Standard Preparations, Standard Injections, Statistics, or SST is missing")

    prep_area = field_by_key(std_preps, "area")
    injection_area = field_by_key(std_injections, "area")
    if injection_area.get("kind") != "calculated":
        raise RuntimeError("Standard Injections is not in its expected read-only form")

    prep_area["hidden"] = True
    index = next(
        index for index, group in enumerate(definition["groups"]) if group.get("key") == "std_injections"
    )
    definition["groups"][index] = editable_standard_group(std_injections)

    stat_fields = {field.get("key"): field for field in stats.get("fields", [])}
    required_stats = {"mean_std", "sd_std", "rsd_std", "mean_bkt", "sd_bkt", "rsd_bkt"}
    if not required_stats.issubset(stat_fields):
        raise RuntimeError("Standard statistics fields are incomplete")
    stat_fields["mean_std"]["expression"] = "mean(std_injections.area)"
    stat_fields["sd_std"]["expression"] = "sd(std_injections.area)"
    stat_fields["rsd_std"]["expression"] = "rsd(std_injections.area)"
    stat_fields["mean_bkt"]["expression"] = "mean(pool(std_injections.area, bkt.area))"
    stat_fields["sd_bkt"]["expression"] = "sd(pool(std_injections.area, bkt.area))"
    stat_fields["rsd_bkt"]["expression"] = "rsd(pool(std_injections.area, bkt.area))"

    field_by_key(sst, "area_lena2_std")["expression"] = "std_injections.area[0]"
    return definition


def migrated_standard_rows(values: dict[str, Any]) -> list[dict[str, Any]] | None:
    existing_rows = values.get("std_injections") or []
    existing_areas = [row.get("area") for row in existing_rows if isinstance(row, dict)]
    prep_rows = values.get("std_preps") or []
    prep_areas = [row.get("area") for row in prep_rows if isinstance(row, dict)]
    source = existing_areas if any(nonblank(area) for area in existing_areas) else prep_areas
    last_nonblank = max((index for index, area in enumerate(source) if nonblank(area)), default=-1)
    if last_nonblank < 0:
        return None
    if last_nonblank >= 6:
        raise RuntimeError("More than six standard injection areas need a manual migration")
    return [{"area": area} for area in source[: last_nonblank + 1]]


def migrate_group_values(raw: str) -> dict[str, Any]:
    values = json.loads(raw or "{}")
    rows = migrated_standard_rows(values)
    if rows is None:
        values.pop("std_injections", None)
    else:
        values["std_injections"] = rows
    return values


def source_example_values(definition: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    standard_areas = [10715758, 10706105, 10682530, 10682530, 10689079]
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
        "std_injections": [{"area": area} for area in standard_areas],
        "bkt": [
            {"area": area}
            for area in [10773612, 10768957, 10794726, 10811829, 10834226, 10830705]
        ],
        "sample_prep": [
            {
                "sample_weight": 60.41,
                "s_vol_1": 100,
                "s_pip_1": 1,
                "s_vol_2": 1,
                "s_pip_2": 1,
                "s_vol_3": 1,
                "av_wt": 1,
                "lc_mg": 1,
            }
        ],
        "sst": [{"area_lena2_sensitivity": 4388, "dilution_factor": 2000}],
        "sst_criteria": [{}, {}, {}, {"result": "23.032"}],
        "impurities": [dict(row) for row in groups["impurities"]["rows"]["seed"]],
        "known_impurities": [dict(row) for row in groups["known_impurities"]["rows"]["seed"]],
    }
    return context, values


def validate_source_example(evaluator: WorksheetEvaluator, definition: dict[str, Any]) -> None:
    context, values = source_example_values(definition)
    result = evaluator.evaluate(context, values)
    stats = result.values
    expected_stats = {
        "stats.mean_std": 10695200.0,
        "stats.sd_std": 15000.62,
        "stats.rsd_std": 0.14,
        "stats.mean_bkt": 10753642.0,
        "stats.sd_bkt": 60097.12,
        "stats.rsd_bkt": 0.56,
    }
    for key, expected in expected_stats.items():
        if stats[key] != expected:
            raise RuntimeError(f"Standard statistic mismatch for {key}: {stats[key]}")
    if result.values["summary.total_all"] != 0.144:
        raise RuntimeError(f"Impurity total mismatch: {result.values['summary.total_all']}")


def backup_database() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"lims.db.bak-a4editstdinj-{stamp}")
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
            print(f"valid={CODE} v{VERSION}; standard_rows=1..6; default=5")
            print("source_example=mean=10695200; sd=15000.62; rsd=0.14; BKT RSD=0.56")
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
        print(f"template={CODE} v{VERSION} id={template_id}; Standard Injections is editable")
        print(f"migrated_in_progress_worksheets={len(migrated_values)}")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
