"""One-off: TPL-A3-0001 "Standard Replicate Injections" -> "Standard Area in Media".

Mirrors the "STD Area in Media" block of `Test types/Saturation solubility by HPLC.xlsx`
(rows 16-26): one STD-area column per media, rows "Standard - 1..6", and a
Mean / SD / RSD row under every media column.

* `std_areas` ("Standard Area in Media"): area columns media_1..media_10.
  - Six media columns are in use by default; Add / Delete Column change the
    number in use (1..10). Media n is shown while media_names.media_count >= n.
  - Column headers are the editable media names (media_names.media_n), falling
    back to "Media n" while a name is blank.
  - Rows are labelled "Standard - 1..N": 6 by default, Add / Delete Row 1..10.
  - Footer: Mean (0 dp), SD (2 dp), RSD (2 dp) under each media column.
* `media_names` (new, not shown as its own section): media_count plus the media
  names. New worksheets are seeded with media_count = 6.
* `stats`: mean/sd/rsd per media column (mean_mN / sd_mN / rsd_mN). Media beyond
  media_count are blank. No longer shown as its own section (the table footer
  shows the same values).
* `samples.solubility` divides by the first media column's mean (stats.mean_m1),
  in place of the old single-column mean.
* SST `sst_std_rsd`: the highest RSD across the media columns in use, NMT 2.0 %.

Worksheets already on the template: their `std_areas` rows (old single `area`
column) are replaced by six blank media rows and `media_names` gets
media_count = 6. Aborts if any old STD area holds a value, since that value has no
column to go to. Other groups are left as stored.

Writes `test_templates.definition` for TPL-A3-0001 v1 and `test_worksheets.group_values`
for its worksheets, in one transaction, after taking a backup
`lims.db.bak-a3media-<timestamp>`. Run with --validate-only first.
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
MAX_MEDIA = 10
DEFAULT_MEDIA = 6
MAX_STD_ROWS = 10
DEFAULT_STD_ROWS = 6
MEDIA = range(1, MAX_MEDIA + 1)
COUNT_REF = "media_names.media_count"

#  The sheet's example (Standard - 1..5; Standard - 6 left blank), same in every media.
SHEET_STD = [1264265, 1266600, 1267571, 1267739, 1266671, None]


def _gated(n: int, expression: str) -> str:
    """Media n contributes only while it is one of the columns in use."""
    if n == 1:
        return expression
    return f"if({COUNT_REF} >= {n}, {expression}, blank())"


def _footer_row(label: str, prefix: str, digits: int) -> list[dict]:
    rounding = {"mode": "round", "digits": digits}
    row = [{"label": label, "ref": f"stats.{prefix}_m1", "rounding": rounding}]
    row += [{"ref": f"stats.{prefix}_m{n}", "rounding": rounding} for n in MEDIA if n > 1]
    return row


def _media_names_group() -> dict:
    return {
        "key": "media_names",
        "kind": "singleton",
        "label": "Media Name",
        #  UI-only: stored and seeded, but edited through the media table header.
        "hidden": True,
        "rows": {"seed": [{"media_count": DEFAULT_MEDIA}]},
        "fields": [
            {
                "key": "media_count",
                "kind": "input",
                "label": "Media columns in use",
                "default": DEFAULT_MEDIA,
            },
            *(
                {"key": f"media_{n}", "kind": "input", "type": "text", "label": f"Media {n}"}
                for n in MEDIA
            ),
        ],
    }


def _std_areas_group() -> dict:
    fields = []
    for n in MEDIA:
        f = {
            "key": f"media_{n}",
            "kind": "area",
            "label": f"Media {n}",
            "labelFrom": f"media_names.media_{n}[0]",
        }
        if n > 1:
            f["showIf"] = f"{COUNT_REF}[0] >= {n}"
        fields.append(f)
    return {
        "key": "std_areas",
        "kind": "table",
        "label": "Standard Area in Media",
        "rows": {"min": 1, "max": MAX_STD_ROWS, "default": DEFAULT_STD_ROWS},
        #  UI-only: lead column captions the rows and the footer rows.
        "rowLabel": {"header": "Media Name", "format": "Standard - {n}"},
        #  UI-only: Add / Delete Column and the editable media-name headers.
        "columnSet": {
            "columns": [f"media_{n}" for n in MEDIA],
            "countRef": COUNT_REF,
            "min": 1,
        },
        "fields": fields,
        "footer": _footer_row("Mean", "mean", 0) + _footer_row("SD", "sd", 2) + _footer_row("RSD", "rsd", 2),
    }


def _stats_group(old: dict) -> dict:
    fields = []
    for n in MEDIA:
        col = f"std_areas.media_{n}"
        fields += [
            {"key": f"mean_m{n}", "kind": "calculated", "label": f"Media {n} Mean",
             "expression": _gated(n, f"mean({col})")},
            {"key": f"sd_m{n}", "kind": "calculated", "label": f"Media {n} SD",
             "expression": _gated(n, f"sd({col})")},
            {"key": f"rsd_m{n}", "kind": "calculated", "label": f"Media {n} RSD", "unit": "%",
             "expression": _gated(n, f"rsd({col})")},
        ]
    new = copy.deepcopy(old)
    new["hidden"] = True
    new["fields"] = fields
    return new


def mutate(definition: dict) -> dict:
    new = copy.deepcopy(definition)
    by = {g["key"]: g for g in new["groups"]}
    assert "media_names" not in by, "already applied"
    std = by["std_areas"]
    assert std["label"] == "Standard Replicate Injections", std["label"]
    assert [f["key"] for f in std["fields"]] == ["area"], std["fields"]

    groups = []
    for g in new["groups"]:
        if g["key"] == "std_areas":
            groups += [_media_names_group(), _std_areas_group()]
        elif g["key"] == "stats":
            groups.append(_stats_group(g))
        else:
            groups.append(g)
    new["groups"] = groups

    sol = next(f for f in by["samples"]["fields"] if f["key"] == "solubility")
    assert "stats.mean_std" in sol["expression"], sol["expression"]
    sol["expression"] = sol["expression"].replace("stats.mean_std", "stats.mean_m1")

    sst = next(c for c in new["criteria"] if c["key"] == "sst_std_rsd")
    assert sst["target"] == "stats.rsd_std", sst["target"]
    sst["target"] = "max(" + ", ".join(f"stats.rsd_m{n}" for n in MEDIA) + ")"
    sst["label"] = "%RSD of standard area in media (highest media)"
    return new


def migrate_worksheet(group_values: dict) -> dict:
    """New-shape std_areas / media_names; every other group kept as stored."""
    gv = copy.deepcopy(group_values or {})
    old_rows = gv.get("std_areas") or []
    filled = [r for r in old_rows if any(v not in (None, "") for v in (r or {}).values())]
    if filled:
        raise SystemExit(f"ABORT: worksheet has old STD areas with values {filled}; reconcile first")
    gv["std_areas"] = [{f"media_{n}": None for n in MEDIA} for _ in range(DEFAULT_STD_ROWS)]
    gv.setdefault("media_names", [{"media_count": DEFAULT_MEDIA}])
    return gv


# ─────────────────────────── checks ───────────────────────────

def _std_rows(columns: dict[int, list]) -> list[dict]:
    """{media n: [areas per standard]} -> std_areas rows."""
    n_rows = max(len(v) for v in columns.values())
    return [{f"media_{n}": vals[i] if i < len(vals) else None for n, vals in columns.items()}
            for i in range(n_rows)]


def check(old_def: dict, new_def: dict, worksheets: list[tuple[int, dict, dict]]) -> None:
    new_p = TemplateDefinition.parse(new_def)
    assert new_p.result_ref == "samples.mean_solubility"
    ev_new = WorksheetEvaluator(new_p)
    ev_old = WorksheetEvaluator(TemplateDefinition.parse(old_def))

    #  0. Shape.
    assert [g.key for g in new_p.groups] == ["standard", "media_names", "std_areas", "stats", "samples"]
    assert new_p.group("std_areas").rows.default == 6 and new_p.group("std_areas").rows.max == 10
    assert new_p.group("media_names").rows.seed == ({"media_count": 6},)
    assert sum(1 for g, _ in new_p.area_field_refs if g == "std_areas") == MAX_MEDIA
    #  Every footer ref resolves to a stats field, 10 per row, in column order.
    footer = new_def["groups"][2]["footer"]
    stat_keys = {f.key for f in new_p.group("stats").fields}
    assert len(footer) == 30 and all(i["ref"].split(".")[1] in stat_keys for i in footer)
    assert [i["ref"] for i in footer[:10]] == [f"stats.mean_m{n}" for n in MEDIA]

    #  1. Empty worksheet evaluates; nothing blocks while blank.
    empty = ev_new.evaluate({}, {})
    assert empty.has_blocking_failure is False
    assert len(empty.rows["std_areas"]) == 6
    assert empty.values["media_names.media_count"] == 6

    #  2. The sheet's example in all six media -> Mean 1266569, SD 1386.78, RSD 0.11.
    gv = {"media_names": [{"media_count": 6}],
          "std_areas": _std_rows({n: SHEET_STD for n in range(1, 7)})}
    r = ev_new.evaluate({}, gv)
    for n in range(1, 7):
        mean, sd, rsd = (r.values[f"stats.{k}_m{n}"] for k in ("mean", "sd", "rsd"))
        assert (f"{mean:.0f}", f"{sd:.2f}", f"{rsd:.2f}") == ("1266569", "1386.78", "0.11"), (n, mean, sd, rsd)
    for n in range(7, 11):
        assert r.values[f"stats.mean_m{n}"] is EMPTY
    sst = next(c for c in r.criteria if c.key == "sst_std_rsd")
    assert sst.passed is True and abs(sst.observed - 0.109491) < 1e-5
    print("sheet example: Mean %.0f, SD %.2f, RSD %.2f in media 1-6; SST observed %.4f -> pass"
          % (r.values["stats.mean_m1"], r.values["stats.sd_m1"], r.values["stats.rsd_m1"], sst.observed))

    #  3. Columns are independent; a column beyond media_count never counts,
    #     even if it still held values.
    noisy = [1000, 1100, 900, 1050, 950, None]  # RSD ~7.9 %
    gv = {"media_names": [{"media_count": 6}],
          "std_areas": _std_rows({1: SHEET_STD, 2: SHEET_STD, 7: noisy})}
    r = ev_new.evaluate({}, gv)
    assert r.values["stats.mean_m7"] is EMPTY and r.values["stats.rsd_m7"] is EMPTY
    assert r.values["stats.mean_m3"] is EMPTY  # in use but not filled
    assert next(c for c in r.criteria if c.key == "sst_std_rsd").passed is True
    gv["media_names"] = [{"media_count": 7}]
    r = ev_new.evaluate({}, gv)
    assert abs(r.values["stats.mean_m7"] - 1000) < 1e-9
    sst = next(c for c in r.criteria if c.key == "sst_std_rsd")
    assert sst.passed is False and r.has_blocking_failure is True
    print("media 7 counted only while 7 columns are in use; its RSD %.2f %% then fails the SST"
          % r.values["stats.rsd_m7"])

    #  4. Solubility = old formula with the first media column's mean as the standard.
    std = [50000.0, 50000.0]
    common = {
        "standard": [{"weight_mg": 10, "vol_1": 10}],
        "samples": [{"area": 25000.0, "aliquot_ml": 1, "diluted_to_ml": 10}],
    }
    r_old = ev_old.evaluate({}, {**common, "std_areas": [{"area": a} for a in std]})
    r_new = ev_new.evaluate({}, {**common, "media_names": [{"media_count": 6}],
                                 "std_areas": _std_rows({1: std, 2: [99999.0, 99999.0]})})
    sol_old, sol_new = r_old.row_value("samples", 0, "solubility"), r_new.row_value("samples", 0, "solubility")
    assert sol_old == sol_new == 5.0, (sol_old, sol_new)
    assert r_old.reportable_result == r_new.reportable_result == 5.0
    print("solubility with media 1 as the standard:", sol_new, "(same as before)")

    #  5. The worksheets on the template still evaluate after migration, data kept.
    for ws_id, before, after in worksheets:
        for key in before:
            if key != "std_areas":
                assert after[key] == before[key], (ws_id, key)
        res = ev_new.evaluate({}, after)
        assert len(res.rows["std_areas"]) == 6
        print(f"worksheet {ws_id}: migrated; groups kept as stored:",
              sorted(k for k in before if k != "std_areas"))


def backup(db: sqlite3.Connection) -> Path:
    target = DB.with_name(f"{DB.name}.bak-a3media-{datetime.now():%Y%m%d-%H%M%S}")
    dst = sqlite3.connect(target)
    with dst:
        db.backup(dst)
    dst.close()
    assert target.stat().st_size > 0
    return target


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate-only", action="store_true")
    args = ap.parse_args()

    db = sqlite3.connect(DB)
    tid, status, raw = db.execute(
        "select id, status, definition from test_templates where code=? and version=1", (CODE,)
    ).fetchone()
    old = json.loads(raw)
    new = mutate(old)

    worksheets = []
    for ws_id, gv_raw in db.execute(
        "select id, group_values from test_worksheets where template_id=?", (tid,)
    ).fetchall():
        raw_group_values = gv_raw or "{}"
        before = json.loads(raw_group_values)
        worksheets.append((ws_id, raw_group_values, before, migrate_worksheet(before)))

    check(old, new, [(ws_id, before, after) for ws_id, _raw, before, after in worksheets])
    if args.validate_only:
        print("--validate-only: no DB write")
        return

    print("backup:", backup(db))
    with db:
        #  Compare the original JSON in the WHERE clause. If an analyst or
        #  template administrator saved meanwhile, abort and roll the whole
        #  transaction back instead of overwriting their newer values.
        cur = db.execute(
            "update test_templates set definition=? where id=? and version=1 and definition=?",
            (json.dumps(new), tid, raw),
        )
        assert cur.rowcount == 1, "template changed while preparing migration"
        for ws_id, raw_group_values, _before, after in worksheets:
            cur = db.execute(
                "update test_worksheets set group_values=? where id=? and group_values=?",
                (json.dumps(after), ws_id, raw_group_values),
            )
            assert cur.rowcount == 1, f"worksheet {ws_id} changed while preparing migration"
    assert json.loads(db.execute("select definition from test_templates where id=?", (tid,)).fetchone()[0]) == new
    assert db.execute("select status from test_templates where id=?", (tid,)).fetchone()[0] == status
    for ws_id, _raw_group_values, _before, after in worksheets:
        stored = json.loads(db.execute("select group_values from test_worksheets where id=?", (ws_id,)).fetchone()[0])
        assert stored == after
    print("written and re-read equal; template status:", status, "; worksheets:", [w[0] for w in worksheets])


if __name__ == "__main__":
    main()
