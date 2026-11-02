"""Add the source-sheet known-impurity calculation table to TPL-A4-0003 v1.

The table is inserted immediately below the existing unknown-impurity table.
It mirrors the source workbook's RRT, raw % impurity, reporting value, known
subtotal, and known-plus-unknown total while retaining the existing unknown
calculation table unchanged apart from hidden reporting-total support.
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
ACTOR = "kiro-a4knownimpurities"
RRF_MULTIPLY = "RRF (multiplication factor)"


# Rows 101..134 from the supplied worksheet. Calculation rows carry the source
# inputs; Hetero/Gilead cross-reference rows retain only their impurity names.
KNOWN_CALC_ROWS: tuple[dict[str, Any], ...] = (
    {
        "name": "1) Emcure: Amine  + N-Acetyl Imp. (RRT-0.60)",
        "rt": 13.386,
        "area": 1707,
        "loq": 0.05,
        "rrf": 0.9,
        "include_calculation": True,
    },
    {"name": "Hetero:LCV3 Monomesyl + Acetyl (RRT-0.60)", "include_calculation": False},
    {"name": "Gilead : GS-832077 + GS-837509 (RRT-0.60)", "include_calculation": False},
    {
        "name": "2) Emcure: Keto imp. (RRT-0.90)",
        "loq": 0.05,
        "rrf": 1.1,
        "include_calculation": True,
    },
    {"name": "Hetero: LCV Keto (RRT-0.90)", "include_calculation": False},
    {"name": "Gilead : GS-833248 (RRT-0.90)", "include_calculation": False},
    {
        "name": "3) Emcure: Deschloro (RRT-0.91)",
        "rt": 21.187,
        "area": 316,
        "loq": 0.05,
        "rrf": 1.4,
        "include_calculation": True,
    },
    {"name": "Hetero: Des Chloro (RRT-0.91)", "include_calculation": False},
    {"name": "Gilead : GS-837322 (RRT-0.91)", "include_calculation": False},
    {
        "name": "4) Emcure :Hydroxide Impurity (RRT-1.03)",
        "loq": 0.08,
        "rrf": 1.15,
        "include_calculation": True,
    },
    {
        "name": "5) Emcure: LCA-VI (RRT-1.20)",
        "rt": 29.485,
        "area": 2257,
        "loq": 0.05,
        "rrf": 1.4,
        "include_calculation": True,
    },
    {"name": "Hetero: Amine  (RRT-1.20)", "include_calculation": False},
    {"name": "Gilead : LENA-2078 or GS-832078 (RRT-1.20)", "include_calculation": False},
    {
        "name": "6) Emcure: Double bond (RRT-1.49)",
        "rt": 35.994,
        "area": 2676,
        "loq": 0.05,
        "rrf": 0.8,
        "include_calculation": True,
    },
    {"name": "Hetero: Double bond (RRT-1.49)", "include_calculation": False},
    {"name": "Gilead : GS-968750 (RRT-1.49)", "include_calculation": False},
    {
        "name": "7) Emcure: Chloromethyl imp. (RRT-0.86)",
        "loq": 0,
        "rrf": 0,
        "include_calculation": True,
    },
    {"name": "Hetero: MSC amine (RRT-0.86)", "include_calculation": False},
    {"name": "Gilead : GS-833244 (RRT-0.86)", "include_calculation": False},
    {
        "name": "8) Emcure: Des Bromo Imp(RRT-0.88)",
        "loq": 0,
        "rrf": 0,
        "include_calculation": True,
    },
    {"name": "Hetero: Des Bromo Imp (RRT-0.88)", "include_calculation": False},
    {"name": "Gilead : GS-833150 (RRT-0.88)", "include_calculation": False},
    {
        "name": "9) Emcure: LCA-V imp.(RRT-1.08)",
        "loq": 0,
        "rrf": 0,
        "include_calculation": True,
    },
    {"name": "Hetero: Bromo Impurity (RRT-1.08)", "include_calculation": False},
    {
        "name": ")Gilead : LENA-2076 or GS-832076) (RRT-1.08)",
        "include_calculation": False,
    },
    {
        "name": "10) Emcure: LCA-VII (RRT-1.21)",
        "loq": 0,
        "rrf": 0,
        "include_calculation": True,
    },
    {"name": "Hetero: LKH-IV(i) / LCV(i) / LSN(i) (RRT-1.21)", "include_calculation": False},
    {"name": "Gilead :LENA-3243 or GS-833243(RRT-1.21)", "include_calculation": False},
    {
        "name": "11) Emcure: Methyl Impurity (RRT-1.26)",
        "loq": 0,
        "rrf": 0,
        "include_calculation": True,
    },
    {"name": "Hetero: Methyl Impurity (RRT-1.26)", "include_calculation": False},
    {"name": "Gilead : GS-828793 (RRT-1.26)", "include_calculation": False},
    {
        "name": "12) Emcure: Ethyl Impurity (RRT-1.34)",
        "loq": 0,
        "rrf": 0,
        "include_calculation": True,
    },
    {"name": "Hetero: Ethyl Impurity (RRT-1.34)", "include_calculation": False},
    {"name": "Gilead : GS-941756 (RRT-1.34)", "include_calculation": False},
)


def known_seed_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in KNOWN_CALC_ROWS]


REPORTED_NUMERIC_FIELD = {
    "key": "reported_numeric",
    "kind": "calculated",
    "expression": (
        "if(include_calculation, if(pct_raw < loq, 0, round(pct_raw, 3)), blank())"
    ),
    "hidden": True,
}


def known_impurity_group(impurity_fields: list[dict[str, Any]]) -> dict[str, Any]:
    fields = [
        dict(field)
        for field in impurity_fields
        if field.get("key") not in {"is_unknown", "reported_numeric"}
    ]
    reported_index = next(
        index for index, field in enumerate(fields) if field.get("key") == "reported"
    )
    fields.insert(reported_index + 1, dict(REPORTED_NUMERIC_FIELD))
    seed = known_seed_rows()
    return {
        "key": "known_impurities",
        "kind": "table",
        "label": "Calculation of Known impurities against standard",
        "showRowNumbers": False,
        "rows": {"min": len(seed), "max": len(seed), "default": len(seed), "seed": seed},
        "fields": fields,
    }


def summary_group() -> dict[str, Any]:
    unknown_pct = "where(impurities.pct_raw, impurities.is_unknown)"
    unknown_reported = "where(impurities.reported_numeric, impurities.is_unknown)"
    return {
        "key": "summary",
        "kind": "singleton",
        "label": "Impurity Summary",
        "fields": [
            {
                "key": "max_single_unknown",
                "kind": "calculated",
                "label": "Single maximum unknown impurity",
                "unit": "%",
                "expression": f"max({unknown_pct})",
                "rounding": {"mode": "round", "digits": 4},
            },
            {
                "key": "max_single_unknown_reported",
                "kind": "calculated",
                "label": "Single maximum unknown impurity — Reporting % Impurity",
                "unit": "%",
                "expression": f"round(max({unknown_reported}), 3)",
                "rounding": {"mode": "round", "digits": 3},
            },
            {
                "key": "total_unknowns",
                "kind": "calculated",
                "label": "Total unknown impurities",
                "unit": "%",
                "expression": f"round(sum({unknown_pct}), 3)",
                "rounding": {"mode": "round", "digits": 4},
            },
            {
                "key": "total_unknowns_reported",
                "kind": "calculated",
                "label": "Total unknown impurities — Reporting % Impurity",
                "unit": "%",
                "expression": f"round(sum({unknown_reported}), 3)",
                "rounding": {"mode": "round", "digits": 3},
            },
            {
                "key": "total_knowns",
                "kind": "calculated",
                "label": "Total of known impurities",
                "unit": "%",
                "expression": "round(sum(known_impurities.pct_raw), 3)",
                "rounding": {"mode": "round", "digits": 4},
            },
            {
                "key": "total_knowns_reported",
                "kind": "calculated",
                "label": "Total of known impurities — Reporting % Impurity",
                "unit": "%",
                "expression": "round(sum(known_impurities.reported_numeric), 3)",
                "rounding": {"mode": "round", "digits": 3},
            },
            {
                "key": "total_all",
                "kind": "calculated",
                "label": "Total known+ unknown impurities",
                "unit": "%",
                "expression": "round(total_knowns + total_unknowns, 3)",
                "rounding": {"mode": "round", "digits": 4},
            },
            {
                "key": "total_all_reported",
                "kind": "calculated",
                "label": "Total known+ unknown impurities — Reporting % Impurity",
                "unit": "%",
                "expression": "round(total_knowns_reported + total_unknowns_reported, 3)",
                "rounding": {"mode": "round", "digits": 3},
            },
        ],
    }


def source_example_values(impurity_seed: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    standard_areas = [10715758, 10706105, 10682530, 10682530, 10689079, None]
    standard_rows = [
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
            "area": area,
        }
        for area in standard_areas
    ]
    context = {"rrf_mode": RRF_MULTIPLY}
    values = {
        "std_preps": standard_rows,
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
        "sst_criteria": [{}, {}, {}, {"result": "23.032"}],
        "impurities": [dict(row) for row in impurity_seed],
        "known_impurities": known_seed_rows(),
    }
    return context, values


def validate_source_example(evaluator: WorksheetEvaluator, impurity_seed: list[dict[str, Any]]) -> None:
    context, values = source_example_values(impurity_seed)
    result = evaluator.evaluate(context, values)
    rows = {row["name"]: row for row in result.rows["known_impurities"]}
    checks = {
        "1) Emcure: Amine  + N-Acetyl Imp. (RRT-0.60)": (0.58, 0.0144, "BLQ"),
        "3) Emcure: Deschloro (RRT-0.91)": (0.92, 0.0042, "BLQ"),
        "5) Emcure: LCA-VI (RRT-1.20)": (1.28, 0.0297, "BLQ"),
        "6) Emcure: Double bond (RRT-1.49)": (1.56, 0.0201, "BLQ"),
    }
    for name, expected in checks.items():
        actual = (rows[name]["rrt"], rows[name]["pct"], rows[name]["reported"])
        if actual != expected:
            raise RuntimeError(f"Known impurity source mismatch for {name}: {actual}")

    summary = result.values
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
        if summary[key] != expected:
            raise RuntimeError(f"Summary source mismatch for {key}: {summary[key]}")


def proposed_definition(raw_definition: str) -> dict[str, Any]:
    definition = json.loads(raw_definition)
    groups = definition.get("groups") or []
    impurities = next((group for group in groups if group.get("key") == "impurities"), None)
    if impurities is None:
        raise RuntimeError("Unknown impurity calculation group is missing")
    if any(group.get("key") == "known_impurities" for group in groups):
        raise RuntimeError("Known impurity calculation group already exists")

    fields = impurities.get("fields") or []
    if not all(any(field.get("key") == key for field in fields) for key in ("pct_raw", "reported", "is_unknown")):
        raise RuntimeError("Unknown impurity calculation fields are incomplete")
    if any(field.get("key") == "reported_numeric" for field in fields):
        raise RuntimeError("Unknown impurity reported-total field already exists")

    reported_index = next(index for index, field in enumerate(fields) if field.get("key") == "reported")
    fields.insert(reported_index + 1, dict(REPORTED_NUMERIC_FIELD))
    known = known_impurity_group(fields)
    summary = summary_group()

    next_groups: list[dict[str, Any]] = []
    inserted = False
    for group in groups:
        if group.get("key") == "summary":
            continue
        next_groups.append(group)
        if group.get("key") == "impurities":
            next_groups.extend((known, summary))
            inserted = True
    if not inserted:
        raise RuntimeError("Unknown impurity calculation group is missing")

    definition["groups"] = next_groups
    definition["resultRef"] = "summary.total_all"
    return definition


def migrate_group_values(raw: str) -> dict[str, Any]:
    values = json.loads(raw or "{}")
    if "known_impurities" in values:
        raise RuntimeError("Worksheet already has a known_impurities group")
    values["known_impurities"] = known_seed_rows()
    return values


def backup_database() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"lims.db.bak-a4knownimpurities-{stamp}")
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
        impurities = next(group for group in definition["groups"] if group.get("key") == "impurities")
        impurity_seed = impurities["rows"]["seed"]
        validate_source_example(evaluator, impurity_seed)

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
            print(f"valid={CODE} v{VERSION}; known_rows={len(known_seed_rows())}")
            print("source_example=known total=0.0680/0.000; known+unknown total=0.1440/0.065")
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
        print(f"template={CODE} v{VERSION} id={template_id}; known_rows={len(known_seed_rows())}")
        print(f"migrated_in_progress_worksheets={len(migrated_values)}")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
