"""Build the single Lenacapavir impurity table from the source worksheet.

This replaces the separate Known Impurities and Unknown Impurities sections in
active TPL-A4-0003 v1 with one fixed, 51-row calculation table positioned below
SST Criteria. It keeps the source worksheet's RRT, raw % impurity, reporting,
and unknown-impurity summary behavior.
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
ACTOR = "kiro-a4combinedimpurities"
RRF_MULTIPLY = "RRF (multiplication factor)"


# Rows 46..69 of the supplied source worksheet. Formula rows reproduce the
# zero-valued Emcure entries, while reference-only GS/LENA rows stay blank
# outside the Impurity column as they do in the workbook.
KNOWN_ROWS: tuple[dict[str, Any], ...] = (
    {
        "name": "Emcure: Atropisomer of Amine Imp. (RRT-0.46)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "GS-832077 (LCV3 Monomesyl) Peak-1 (RRT-0.46)",
        "include_calculation": False,
        "is_unknown": False,
    },
    {
        "name": "Emcure:Atropisomer- N-Acetyl Imp.(RRT-0.49)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "GS-837509 (Acetyl Impurity) Peak-1(RRT-0.49)",
        "include_calculation": False,
        "is_unknown": False,
    },
    {
        "name": "Emcure:Atropisomer-Trifluoro acetyl (RRT-0.63)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "Emcure: Atropisomer - Keto Imp. (RRT-0.80)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "GS-833248 (LCV Keto) Peak-1(RRT-0.80)",
        "include_calculation": False,
        "is_unknown": False,
    },
    {
        "name": "Emcure: Atropisomer-Chloromethyl (RRT-0.81)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "GS-833244 (MSC Amine) Peak-1 (RRT-0.81)",
        "include_calculation": False,
        "is_unknown": False,
    },
    {
        "name": "Emcure: Atropisomer - Deschloro (RRT-0.85)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "GS-837322 (Deschloro) Peak-1 (RRT-0.85)",
        "include_calculation": False,
        "is_unknown": False,
    },
    {
        "name": "Emcure: Atropisomer - LCA-VI (RRT-1.13)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "LENA-2078/GS-832078(Amine) Peak-1(RRT-1.13)",
        "include_calculation": False,
        "is_unknown": False,
    },
    {
        "name": "Emcure:Atropisomer - LCA-VII (RRT-1.18)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "LENA-3243/GS-833243(LKH-IV(i)) Peak-1_(RRT-1.18)",
        "include_calculation": False,
        "is_unknown": False,
    },
    {
        "name": "Emcure: Atropisomer - Methyl imp (RRT-1.20)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "GS-828793 (Methyl imp) Peak-1(RRT-1.20)",
        "include_calculation": False,
        "is_unknown": False,
    },
    {
        "name": "Emcure: Atropisomer - Ethyl imp (RRT-1.29)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "GS-941756 (Ethyl imp) Peak-1 (RRT-1.29)",
        "include_calculation": False,
        "is_unknown": False,
    },
    {
        "name": "Emcure: Atropisomer - Double bond (RRT-1.37)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "GS-968750 (Double bond) Peak-1 (RRT-1.37)",
        "include_calculation": False,
        "is_unknown": False,
    },
    {
        "name": "Emcure:Trifluoroacetyl imp. @ RRT-0.70)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "Emcure:Diene imp. @ RRT-1.56)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
    {
        "name": "Emcure:Allene imp. @ RRT-1.60)",
        "include_calculation": True,
        "is_unknown": False,
        "loq": 0,
        "rrf": 0,
    },
)


def impurity_seed_rows() -> list[dict[str, Any]]:
    rows = [dict(row) for row in KNOWN_ROWS]
    for number in range(1, 28):
        row: dict[str, Any] = {
            "name": f"Unknown-{number}",
            "include_calculation": True,
            "is_unknown": True,
            "loq": 0.05,
            "rrf": 1,
        }
        if number == 1:
            row.update({"rt": 18.393, "area": 1223})
        elif number == 2:
            row.update({"rt": 36.997, "area": 6895})
        rows.append(row)
    return rows


def impurity_group(base_pct_expression: str) -> dict[str, Any]:
    seed = impurity_seed_rows()
    pct_uncorrected = (
        "if(include_calculation, if(isblank(area), 0, "
        f"{base_pct_expression}), blank())"
    )
    return {
        "key": "impurities",
        "kind": "table",
        "label": "Impurity Calculation of unknown impurities against standard",
        "showRowNumbers": False,
        "rows": {"min": len(seed), "max": len(seed), "default": len(seed), "seed": seed},
        "fields": [
            {
                "key": "name",
                "kind": "input",
                "type": "text",
                "label": "Impurity",
                "width": "34%",
            },
            {"key": "rt", "kind": "input", "label": "R.T.", "width": "8%"},
            {"key": "area", "kind": "area", "label": "Area", "width": "11%"},
            {
                "key": "loq",
                "kind": "input",
                "label": "LOQ",
                "rounding": {"mode": "round", "digits": 4},
                "width": "8%",
            },
            {
                "key": "rrf",
                "kind": "input",
                "label": "RRF (multiplication factor)",
                "rounding": {"mode": "round", "digits": 2},
                "width": "15%",
            },
            {
                "key": "rrt",
                "kind": "calculated",
                "label": "RRT",
                "expression": (
                    "if(include_calculation, if(isblank(rt), 0, "
                    "rt / number(sst_criteria.result[3])), blank())"
                ),
                "rounding": {"mode": "round", "digits": 2},
                "width": "7%",
            },
            {
                "key": "pct_uncorrected",
                "kind": "calculated",
                "expression": pct_uncorrected,
                "hidden": True,
            },
            {
                "key": "pct_raw",
                "kind": "calculated",
                "expression": (
                    "if(include_calculation, if(rrf_mode = \"RRF (multiplication factor)\", "
                    "pct_uncorrected * rrf, pct_uncorrected / rrf), blank())"
                ),
                "hidden": True,
            },
            {
                "key": "pct",
                "kind": "calculated",
                "label": "% Impurity",
                "unit": "%",
                "expression": "round(pct_raw, 4)",
                "rounding": {"mode": "round", "digits": 4},
                "width": "8%",
            },
            {
                "key": "reported",
                "kind": "calculated",
                "label": "Reporting % Impurity",
                "expression": (
                    "if(include_calculation, if(pct_raw < loq, \"BLQ\", "
                    "round(pct_raw, 3)), blank())"
                ),
                "rounding": {"mode": "round", "digits": 3},
                "width": "9%",
            },
            {
                "key": "include_calculation",
                "kind": "input",
                "type": "boolean",
                "hidden": True,
            },
            {
                "key": "is_unknown",
                "kind": "input",
                "type": "boolean",
                "hidden": True,
            },
        ],
    }


def summary_group() -> dict[str, Any]:
    unknown_pct = "where(impurities.pct_raw, impurities.is_unknown)"
    return {
        "key": "summary",
        "kind": "singleton",
        "label": "Summary",
        "fields": [
            {
                "key": "max_single_unknown",
                "kind": "calculated",
                "label": "Single maximum unknown impurity (Limit: 0.065)",
                "unit": "%",
                "expression": f"max({unknown_pct})",
                "rounding": {"mode": "round", "digits": 4},
            },
            {
                "key": "total_unknowns",
                "kind": "calculated",
                "label": "Total unknown impurities (Limit: 0.065)",
                "unit": "%",
                "expression": f"round(sum({unknown_pct}), 3)",
                "rounding": {"mode": "round", "digits": 4},
            },
        ],
    }


def legacy_rows_have_entered_values(rows: Any) -> bool:
    if not isinstance(rows, list):
        return False
    for row in rows:
        if not isinstance(row, dict):
            continue
        if any(row.get(key) not in (None, "") for key in ("name", "alt_name", "rt", "rrt", "area")):
            return True
    return False


def migrate_group_values(raw: str) -> dict[str, Any]:
    values = json.loads(raw or "{}")
    if "impurities" in values:
        raise RuntimeError("Worksheet already has an impurities group")
    if legacy_rows_have_entered_values(values.get("known_impurities")) or legacy_rows_have_entered_values(
        values.get("unknowns")
    ):
        raise RuntimeError("Worksheet contains entered impurity data and needs a manual migration")

    values["impurities"] = impurity_seed_rows()
    values.pop("known_impurities", None)
    values.pop("unknowns", None)
    return values


def source_example_values() -> tuple[dict[str, Any], dict[str, Any]]:
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
        "impurities": impurity_seed_rows(),
    }
    return context, values


def validate_source_example(evaluator: WorksheetEvaluator) -> None:
    context, values = source_example_values()
    result = evaluator.evaluate(context, values)
    by_name = {row["name"]: row for row in result.rows["impurities"]}
    unknown_1 = by_name["Unknown-1"]
    unknown_2 = by_name["Unknown-2"]
    if (unknown_1["rrt"], unknown_1["pct"], unknown_1["reported"]) != (0.8, 0.0115, "BLQ"):
        raise RuntimeError(f"Unknown-1 source example mismatch: {unknown_1}")
    if (unknown_2["rrt"], unknown_2["pct"], unknown_2["reported"]) != (1.61, 0.0647, 0.065):
        raise RuntimeError(f"Unknown-2 source example mismatch: {unknown_2}")
    summary = result.values
    if summary["summary.max_single_unknown"] != 0.0647:
        raise RuntimeError(f"Maximum unknown impurity mismatch: {summary['summary.max_single_unknown']}")
    if summary["summary.total_unknowns"] != 0.076:
        raise RuntimeError(f"Total unknown impurities mismatch: {summary['summary.total_unknowns']}")


def proposed_definition(raw_definition: str) -> dict[str, Any]:
    definition = json.loads(raw_definition)
    groups = definition.get("groups") or []
    known = next((group for group in groups if group.get("key") == "known_impurities"), None)
    if known is None:
        raise RuntimeError("Known Impurities group is missing")
    base_pct_field = next(
        (field for field in known.get("fields", []) if field.get("key") == "pct_uncorrected"),
        None,
    )
    if not base_pct_field or not base_pct_field.get("expression"):
        raise RuntimeError("Known Impurities formula is missing")
    if any(group.get("key") == "impurities" for group in groups):
        raise RuntimeError("Combined impurities group already exists")

    combined = impurity_group(base_pct_field["expression"])
    summary = summary_group()
    next_groups: list[dict[str, Any]] = []
    inserted = False
    for group in groups:
        key = group.get("key")
        if key in {"known_impurities", "unknowns", "summary"}:
            continue
        next_groups.append(group)
        if key == "sst_criteria":
            next_groups.extend((combined, summary))
            inserted = True
    if not inserted:
        raise RuntimeError("SST Criteria group is missing")

    definition["groups"] = next_groups
    definition["resultRef"] = "summary.total_unknowns"
    return definition


def backup_database() -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = DB.with_name(f"lims.db.bak-a4combinedimpurities-{stamp}")
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
        validate_source_example(evaluator)

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
            print(f"valid={CODE} v{VERSION}; combined_rows={len(impurity_seed_rows())}")
            print("source_example=Unknown-1 0.0115/BLQ; Unknown-2 0.0647/0.065; total=0.0760")
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
        print(f"template={CODE} v{VERSION} id={template_id}; combined_rows={len(impurity_seed_rows())}")
        print(f"migrated_in_progress_worksheets={len(migrated_values)}")
        return 0
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())
