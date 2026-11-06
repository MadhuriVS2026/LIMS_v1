"""
Tests for the live-catalogue half of scripts/standard_tabular_rollout.py.

A small sqlite file is built per test with the live ``test_templates`` /
``test_worksheets`` columns. It holds three roster templates in their pre-rollout
(singleton) form, one roster row that is already tabular, one Inactive row and one
decoy singleton in a non-roster group. The real lims.db is never opened here.
"""
import copy
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts import standard_tabular_rollout as rollout
from scripts.standard_tabular_rollout import (
    ACTOR,
    BACKUP_INFIX,
    ROSTER,
    RolloutError,
    apply_changes,
    fingerprint,
    main,
    plan_changes,
    snapshot,
    synthesize_inputs,
    verify,
)
from scripts.template_definitions import SEED_TEMPLATES

_MODULES = {t.code: t for t in SEED_TEMPLATES}
#  A1-0001 and A8-0004 convert `standard`; A4-0001 converts `standard` and `standard_2`;
#  A6B-0002 is already a table in its module.
_CODES = ("TPL-A1-0001", "TPL-A4-0001", "TPL-A8-0004", "TPL-A6B-0002")
_TEST_ROSTER = tuple(e for e in ROSTER if e.code in _CODES)
_EXPECT = {"expected_rows": 6, "expected_statuses": {"Active": 5, "Inactive": 1}}
_NOW = datetime(2026, 11, 5, 9, 30, 15, tzinfo=timezone.utc)

_TEMPLATE_DDL = """
create table test_templates (
    id integer primary key, code varchar(50) not null, name varchar(255) not null,
    archetype varchar(20) not null, test_id integer not null, version integer not null,
    status varchar(20) not null, result_unit varchar(50), definition json not null,
    approved_by varchar(255), approved_at datetime, superseded_by_id integer,
    created_by varchar(255) not null, created_date datetime not null,
    modified_by varchar(255) not null, modified_date datetime not null)
"""
_WORKSHEET_DDL = """
create table test_worksheets (
    id integer primary key, template_id integer not null, context_values json not null,
    group_values json not null)
"""


def _legacy(defn: dict, keys: tuple[str, ...]) -> dict:
    """The pre-rollout shape: converted groups back to singletons."""
    legacy = copy.deepcopy(defn)
    for group in legacy["groups"]:
        if group["key"] in keys and group["kind"] == "table":
            group["kind"] = "singleton"
            group.pop("rows", None)
            group.pop("rowLabel", None)
    return legacy


def _insert(con, tid, code, version, status, defn):
    con.execute(
        "insert into test_templates values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (tid, code, f"name {code}", "A1", 1, version, status, "%", json.dumps(defn),
         None, None, None, "seed", "2026-08-06 12:02:03.055480", "seed", "2026-08-06 12:02:03.055480"),
    )


def _build(path: Path, *, poison: bool = False, drop_standard_2: bool = False) -> None:
    con = sqlite3.connect(path)
    con.execute(_TEMPLATE_DDL)
    con.execute(_WORKSHEET_DDL)
    for entry in _TEST_ROSTER:
        defn = _legacy(_MODULES[entry.code].definition, entry.keys) if entry.code != "TPL-A6B-0002" else copy.deepcopy(
            _MODULES[entry.code].definition
        )
        if poison and entry.code == "TPL-A1-0001":
            defn["groups"][-1]["fields"].append(
                {"key": "poison", "kind": "calculated", "expression": "if(standard.weight_mg, 1, 2)"}
            )
        if drop_standard_2 and entry.code == "TPL-A4-0001":
            defn["groups"] = [g for g in defn["groups"] if g["key"] != "standard_2"]
        _insert(con, entry.template_id, entry.code, entry.version, entry.status, defn)
    #  Inactive row: a superseded copy that still carries a singleton `standard`.
    inactive = _legacy(_MODULES["TPL-A1-0001"].definition, ("standard",))
    _insert(con, 100, "TPL-A1-9999", 1, "Inactive", inactive)
    #  Decoy: a singleton in a group that is not a standard section.
    decoy = {"context": [], "groups": [{"key": "std", "kind": "singleton", "label": "Stock",
                                         "fields": [{"key": "w", "kind": "input"}]}]}
    _insert(con, 101, "TPL-DECOY-0001", 1, "Active", decoy)
    a1 = _legacy(_MODULES["TPL-A1-0001"].definition, ("standard",))
    ctx, groups = synthesize_inputs(a1)
    con.execute("insert into test_worksheets values (1, 1, ?, ?)", (json.dumps(ctx), json.dumps(groups)))
    con.commit()
    con.close()


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "lims.db"
    _build(path)
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path, table: str = "test_templates") -> dict[int, tuple]:
    con = sqlite3.connect(path)
    try:
        return {r[0]: r for r in con.execute(f"select * from {table} order by id")}
    finally:
        con.close()


def _backups(path: Path) -> list[Path]:
    return sorted(path.parent.glob(path.name + BACKUP_INFIX + "*"))


def _apply(path: Path, **kw):
    return apply_changes(path, _TEST_ROSTER, now=_NOW, **_EXPECT, **kw)


class TestFingerprint:
    def test_matching_database_passes(self, db):
        con = sqlite3.connect(db)
        assert fingerprint(con, **_EXPECT) == {"rows": 6, "statuses": {"Active": 5, "Inactive": 1}, "integrity": "ok"}

    def test_a_status_mismatch_is_reported(self, db):
        con = sqlite3.connect(db)
        with pytest.raises(RolloutError, match="status counts"):
            fingerprint(con, 6, {"Active": 4, "Inactive": 2})

    def test_default_expectation_is_the_live_catalogue(self, db):
        con = sqlite3.connect(db)
        with pytest.raises(RolloutError, match="expected 57"):
            fingerprint(con)

    def test_apply_aborts_before_any_write_when_the_fingerprint_is_wrong(self, db):
        before = _sha(db)
        with pytest.raises(RolloutError, match="fingerprint mismatch"):
            apply_changes(db, _TEST_ROSTER, now=_NOW)  # defaults: 57 rows / 48 Active
        assert _sha(db) == before
        assert _backups(db) == []

    def test_cli_refuses_to_apply_on_a_wrong_catalogue(self, db, tmp_path, capsys):
        before = _sha(db)
        code = main(["--db", str(db), "--apply", "--report-dir", str(tmp_path)], roster=_TEST_ROSTER)
        assert code == 2
        assert "fingerprint mismatch" in capsys.readouterr().err
        assert _sha(db) == before and _backups(db) == []


class TestDryRun:
    def test_plan_converts_three_rows_and_skips_the_tabular_one(self, db):
        con = sqlite3.connect(db)
        plan = plan_changes(con, _TEST_ROSTER)
        assert plan.ok, plan.problems
        assert sorted(r.entry.code for r in plan.to_convert) == ["TPL-A1-0001", "TPL-A4-0001", "TPL-A8-0004"]
        assert [r.action for r in plan.rows if r.entry.code == "TPL-A6B-0002"] == ["skip"]
        assert plan.group_count == 4  # standard x3 + standard_2
        assert plan.audit_violations == 0 and plan.equivalence_diffs == 0
        assert all(r.equivalence.coverage_ok for r in plan.to_convert)
        assert all(r.worksheets == (1 if r.entry.code == "TPL-A1-0001" else 0) for r in plan.rows)

    def test_dry_run_writes_nothing_and_reports_the_roster(self, db, tmp_path, capsys):
        before = _sha(db)
        code = main(["--db", str(db), "--dry-run", "--report-dir", str(tmp_path / "out")],
                    roster=_TEST_ROSTER, **_EXPECT)
        assert code == 0
        assert _sha(db) == before
        assert _backups(db) == []
        text = (tmp_path / "out" / "roster.md").read_text(encoding="utf-8")
        for c in _CODES:
            assert c in text
        assert "| convert |" in text and "| skip |" in text
        assert "rows to convert: 3" in capsys.readouterr().out

    def test_a_missing_roster_group_aborts_the_plan(self, tmp_path):
        path = tmp_path / "lims.db"
        _build(path, drop_standard_2=True)
        con = sqlite3.connect(path)
        plan = plan_changes(con, _TEST_ROSTER)
        assert not plan.ok
        assert any("standard_2" in p and "not found" in p for p in plan.problems)
        before = _sha(path)
        with pytest.raises(RolloutError, match="nothing written"):
            _apply(path)
        assert _sha(path) == before and _backups(path) == []


class TestApply:
    def test_apply_changes_only_the_roster_rows_definition_and_modified_columns(self, db):
        before = _rows(db)
        ws_before = _rows(db, "test_worksheets")
        result = _apply(db)
        after = _rows(db)
        assert sorted(result.updated) == ["TPL-A1-0001 v1", "TPL-A4-0001 v1", "TPL-A8-0004 v1"]
        cols = [c[1] for c in sqlite3.connect(db).execute("pragma table_info(test_templates)")]
        mutable = {"definition", "modified_by", "modified_date"}
        for tid in (1, 4, 38):
            changed = {cols[i] for i in range(len(cols)) if before[tid][i] != after[tid][i]}
            assert changed == mutable
            row = dict(zip(cols, after[tid]))
            assert row["modified_by"] == ACTOR == "std-details-rollout"
            assert row["modified_date"] == "2026-11-05 09:30:15.000000"
            assert json.loads(row["definition"]) == _MODULES[row["code"]].definition
        #  Already tabular, Inactive and decoy rows are byte-identical.
        for tid in (37, 100, 101):
            assert after[tid] == before[tid]
        assert _rows(db, "test_worksheets") == ws_before

    def test_standard_2_becomes_a_table_in_a4_0001(self, db):
        _apply(db)
        defn = json.loads(_rows(db)[4][list(_cols(db)).index("definition")])
        groups = {g["key"]: g for g in defn["groups"]}
        for key in ("standard", "standard_2"):
            assert groups[key]["kind"] == "table"
            assert groups[key]["rows"] == {"min": 1, "max": 10, "default": 1}

    def test_backup_exists_and_has_the_same_rows_as_the_pre_state(self, db):
        before = _rows(db)
        result = _apply(db)
        assert result.backup is not None and result.backup.exists()
        assert result.backup.name == "lims.db" + BACKUP_INFIX + "20261105-093015"
        assert _backups(db) == [result.backup]
        assert _rows(result.backup) == before

    def test_second_apply_is_a_no_op(self, db):
        _apply(db)
        after_first = _sha(db)
        again = apply_changes(db, _TEST_ROSTER, now=datetime(2026, 11, 5, 10, 0, 0, tzinfo=timezone.utc), **_EXPECT)
        assert again.updated == [] and again.backup is None
        assert _sha(db) == after_first
        assert len(_backups(db)) == 1

    def test_a_poisoned_definition_aborts_the_whole_run_with_zero_writes(self, tmp_path):
        path = tmp_path / "lims.db"
        _build(path, poison=True)
        before = _sha(path)
        with pytest.raises(RolloutError, match="reference audit"):
            _apply(path)
        assert _sha(path) == before
        assert _backups(path) == []

    def test_a_failed_in_transaction_verify_rolls_everything_back(self, db, monkeypatch):
        before_rows = _rows(db)
        monkeypatch.setattr(rollout, "verify", lambda *a, **k: ["forced failure"])
        with pytest.raises(RolloutError, match="forced failure"):
            _apply(db)
        assert _rows(db) == before_rows
        assert len(_backups(db)) == 1  # the backup was taken before the transaction


def _cols(db: Path) -> list[str]:
    return [c[1] for c in sqlite3.connect(db).execute("pragma table_info(test_templates)")]


class TestVerify:
    def test_verify_passes_after_apply_and_is_read_only(self, db, tmp_path, capsys):
        result = _apply(db)
        done = _sha(db)
        code = main(["--db", str(db), "--verify", "--report-dir", str(tmp_path / "out")],
                    roster=_TEST_ROSTER, **_EXPECT)
        assert code == 0, capsys.readouterr()
        assert _sha(db) == done
        text = (tmp_path / "out" / "roster.md").read_text(encoding="utf-8")
        assert "Verify: all checks passed." in text and str(result.backup.name) in text

    def test_verify_detects_a_change_to_a_row_outside_the_roster(self, db):
        result = _apply(db)
        con = sqlite3.connect(db)
        con.execute("update test_templates set name='tampered' where id=101")
        con.commit()
        pre_con = sqlite3.connect(result.backup)
        failures = verify(con, snapshot(pre_con), _TEST_ROSTER)
        assert any("TPL-DECOY-0001" in f and "not on the roster" in f for f in failures)

    def test_verify_detects_a_definition_that_is_not_the_conversion(self, db):
        result = _apply(db)
        con = sqlite3.connect(db)
        defn = json.loads(con.execute("select definition from test_templates where id=1").fetchone()[0])
        defn["groups"][0]["label"] = "edited"
        con.execute("update test_templates set definition=? where id=1", (json.dumps(defn),))
        con.commit()
        failures = verify(con, snapshot(sqlite3.connect(result.backup)), _TEST_ROSTER, replay=False)
        assert any("not convert(pre-state definition)" in f for f in failures)

    def test_verify_without_a_backup_is_refused(self, db, tmp_path, capsys):
        assert main(["--db", str(db), "--verify", "--report-dir", str(tmp_path)],
                    roster=_TEST_ROSTER, **_EXPECT) == 2
        assert "no pre-state backup" in capsys.readouterr().err
