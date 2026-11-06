

# ══ Part 2: live catalogue sync ══════════════════════════════════════
#
#  Raw sqlite3, in the style of scripts/update_a2_0002_definition.py. The tool never
#  copies a module over a row: it applies ``convert_definition`` to the stored
#  definition, so edits made to the live row since it was seeded are kept.
#
#      python -m scripts.standard_tabular_rollout --db <abs path to lims.db> \
#          (--dry-run | --apply | --verify) [--report-dir <dir>]
#
#  --dry-run and --verify open the database read-only (``mode=ro``). --apply takes
#  a backup first, then writes in one ``BEGIN IMMEDIATE`` transaction.

EXPECTED_ROWS = 57
EXPECTED_STATUSES: dict[str, int] = {"Active": 48, "Draft": 4, "Inactive": 3, "Superseded": 2}
ACTOR = "std-details-rollout"
BACKUP_INFIX = ".bak-std-rollout-"
LOCK_TIMEOUT_S = 30
#  Rows whose ``standard_2`` must be a table after the sync (user's last request).
STANDARD_2_CODES: frozenset[str] = frozenset({"TPL-A4-0001", "TPL-H1-0001", "TPL-H1-0002"})
#  Converted in an earlier commit; the sync only re-verifies it.
REFERENCE_CODE = "TPL-A2-0002"
_TS_FORMAT = "%Y-%m-%d %H:%M:%S.%f"  # what SQLAlchemy stores for DateTime columns


class RolloutError(Exception):
    """A pre-condition or post-condition failed; nothing was (or stays) written."""


def _open_ro(path: str | Path) -> sqlite3.Connection:
    return sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)


def _digest(rows: Iterable[Iterable[Any]]) -> str:
    h = hashlib.sha256()
    for row in rows:
        h.update(repr(tuple(row)).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _group(defn: dict | None, key: str) -> dict | None:
    for g in (defn or {}).get("groups") or []:
        if g.get("key") == key:
            return g
    return None


def _json(text: Any) -> Any:
    if text is None:
        return None
    return json.loads(text) if isinstance(text, (str, bytes)) else text


# ── Fingerprint ──────────────────────────────────────────────────────


def fingerprint(
    con: sqlite3.Connection,
    expected_rows: int = EXPECTED_ROWS,
    expected_statuses: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Confirm this is the catalogue the roster was built against.

    Row count, per-status counts and ``PRAGMA integrity_check`` must all match,
    otherwise ``RolloutError`` is raised before anything is written. The expected
    values are arguments so tests can use a small database.
    """
    expected_statuses = EXPECTED_STATUSES if expected_statuses is None else expected_statuses
    rows = con.execute("select count(*) from test_templates").fetchone()[0]
    statuses = {s: n for s, n in con.execute("select status, count(*) from test_templates group by status")}
    integrity = [r[0] for r in con.execute("pragma integrity_check")]
    problems = []
    if rows != expected_rows:
        problems.append(f"{rows} template rows, expected {expected_rows}")
    if statuses != expected_statuses:
        problems.append(f"status counts {dict(sorted(statuses.items()))}, expected {dict(sorted(expected_statuses.items()))}")
    if integrity != ["ok"]:
        problems.append(f"integrity_check: {integrity[:3]}")
    if problems:
        raise RolloutError("fingerprint mismatch: " + "; ".join(problems))
    return {"rows": rows, "statuses": statuses, "integrity": "ok"}


# ── Plan ─────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _modules() -> dict[str, Any]:
    from scripts.template_definitions import SEED_TEMPLATES

    return {t.code: t for t in SEED_TEMPLATES}


@dataclass
class RowPlan:
    entry: RosterEntry
    row_id: int | None = None
    status: str | None = None
    #  "convert": the stored definition changes. "skip": every group is already a
    #  table. "error": the row cannot be planned.
    action: str = "error"
    old_def: dict | None = None
    new_def: dict | None = None
    #  Group keys whose stored shape changes.
    converted: tuple[str, ...] = ()
    audit: list[str] = field(default_factory=list)
    equivalence: EquivalenceReport | None = None
    worksheets: int = 0
    drift: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


@dataclass
class Plan:
    rows: list[RowPlan]

    @property
    def problems(self) -> list[str]:
        return [f"{r.entry.code} v{r.entry.version}: {p}" for r in self.rows for p in r.problems]

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def to_convert(self) -> list[RowPlan]:
        return [r for r in self.rows if r.action == "convert"]

    @property
    def group_count(self) -> int:
        return sum(len(r.converted) for r in self.rows)

    @property
    def audit_violations(self) -> int:
        return sum(len(r.audit) for r in self.rows)

    @property
    def equivalence_diffs(self) -> int:
        return sum(len(r.equivalence.diffs) for r in self.rows if r.equivalence)


def structural_problems(old: dict, new: dict, keys: Iterable[str]) -> list[str]:
    """
    The structural-diff guard: only the target groups may differ, and only by
    ``kind``, ``rows``, ``rowLabel`` and the removal of ``renderAsTable``.
    """
    keys = tuple(keys)
    problems: list[str] = []
    for k in sorted(set(old) | set(new)):
        if k != "groups" and old.get(k, _MISSING) != new.get(k, _MISSING):
            problems.append(f"top-level key {k!r} changed")
    og, ng = old.get("groups") or [], new.get("groups") or []
    if [g.get("key") for g in og] != [g.get("key") for g in ng]:
        return problems + ["group list or order changed"]
    for o, n in zip(og, ng):
        key = o.get("key")
        if key not in keys:
            if o != n:
                problems.append(f"group {key!r} is not a target but changed")
            continue
        if o.get("kind") == "table":
            if o != n:
                problems.append(f"group {key!r} is already a table but changed")
            continue
        if n.get("kind") != "table":
            problems.append(f"group {key!r} did not become a table")
        if n.get("rows") != STANDARD_ROWS or n.get("rowLabel") != STANDARD_ROW_LABEL:
            problems.append(f"group {key!r} has the wrong rows / rowLabel")
        drop_old, drop_new = {"kind", "renderAsTable", "rows", "rowLabel"}, {"kind", "rows", "rowLabel"}
        if {k: v for k, v in o.items() if k not in drop_old} != {k: v for k, v in n.items() if k not in drop_new}:
            problems.append(f"group {key!r} changed beyond kind/rows/rowLabel/renderAsTable")
    return problems


def _drift(live: dict, module: dict) -> list[str]:
    """Where the live definition differs from its module (informational)."""
    out = [
        k
        for k in sorted(set(live) | set(module))
        if k != "groups" and live.get(k, _MISSING) != module.get(k, _MISSING)
    ]
    lg = {g.get("key"): g for g in live.get("groups") or []}
    mg = {g.get("key"): g for g in module.get("groups") or []}
    for key in list(lg) + [k for k in mg if k not in lg]:
        if lg.get(key) != mg.get(key):
            out.append(f"groups.{key}")
    if not out and [g.get("key") for g in live.get("groups") or []] != list(mg):
        out.append("groups.order")
    return out


def module_check(entry: RosterEntry, new_def: dict) -> tuple[list[str], list[str]]:
    """
    Compare the converted definition with the module, as the roster declares.

    ``equal`` rows must equal the module exactly; ``drifted`` rows must match it on
    ``kind``/``rows``/``rowLabel`` of the converted groups (the drift is listed);
    ``none`` rows must have no module. Returns ``(drift, problems)``.
    """
    module = _modules().get(entry.code)
    if entry.module == "none":
        return [], ([f"roster says DB-only but a module exists for {entry.code}"] if module else [])
    if module is None:
        return [], [f"roster says {entry.module} but no module has code {entry.code}"]
    mdef = module.definition
    drift = _drift(new_def, mdef)
    if entry.module == "equal":
        return drift, ([f"converted definition differs from its module: {drift}"] if new_def != mdef else [])
    problems = []
    for key in entry.keys:
        live_g, mod_g = _group(new_def, key), _group(mdef, key)
        if mod_g is None:
            problems.append(f"module has no group {key!r}")
            continue
        for attr in ("kind", "rows", "rowLabel"):
            if (live_g or {}).get(attr) != mod_g.get(attr):
                problems.append(f"group {key!r} {attr} differs from the module")
    return drift, problems


def _load_worksheets(con: sqlite3.Connection) -> dict[int, list[tuple[dict, dict]]]:
    out: dict[int, list[tuple[dict, dict]]] = {}
    for tid, ctx, groups in con.execute(
        "select template_id, context_values, group_values from test_worksheets order by rowid"
    ):
        out.setdefault(tid, []).append((_json(ctx) or {}, _json(groups) or {}))
    return out


def plan_changes(con: sqlite3.Connection, roster: Iterable[RosterEntry] = ROSTER) -> Plan:
    """
    Plan the sync without writing. Every problem is recorded on its row; the caller
    must refuse to apply a plan that is not ``ok`` (one bad row aborts the run).
    """
    worksheets = _load_worksheets(con)
    rows: list[RowPlan] = []
    for entry in roster:
        rp = RowPlan(entry=entry)
        rows.append(rp)
        found = con.execute(
            "select id, status, definition from test_templates where code=? and version=?",
            (entry.code, entry.version),
        ).fetchall()
        if len(found) != 1:
            rp.problems.append(f"expected 1 row for code+version, found {len(found)}")
            continue
        rp.row_id, rp.status, text = found[0]
        if rp.row_id != entry.template_id:
            rp.problems.append(f"id is {rp.row_id}, roster says {entry.template_id}")
        if rp.status != entry.status:
            rp.problems.append(f"status is {rp.status!r}, expected {entry.status!r}")
        try:
            rp.old_def = _json(text)
        except ValueError as exc:
            rp.problems.append(f"stored definition is not valid JSON: {exc}")
            continue
        if not isinstance(rp.old_def, dict):
            rp.problems.append("stored definition is not an object")
            continue
        try:
            rp.new_def = convert_definition(rp.old_def, entry.keys)
        except ValueError as exc:
            rp.problems.append(str(exc))
            continue
        rp.converted = tuple(
            k for k in entry.keys if _group(rp.old_def, k) != _group(rp.new_def, k)
        )
        rp.action = "convert" if rp.new_def != rp.old_def else "skip"
        rp.problems += structural_problems(rp.old_def, rp.new_def, entry.keys)
        rp.audit = audit_references(rp.old_def, entry.keys)
        rp.problems += [f"reference audit: {v}" for v in rp.audit]
        rp.worksheets = len(worksheets.get(rp.row_id, []))
        try:
            TemplateDefinition.parse(rp.new_def)
        except Exception as exc:  # noqa: BLE001
            rp.problems.append(f"converted definition does not parse: {str(exc)[:200]}")
            continue
        if rp.action == "convert":
            try:
                rp.equivalence = check_equivalence(
                    rp.old_def, rp.new_def, entry.keys, worksheets.get(rp.row_id, [])
                )
            except Exception as exc:  # noqa: BLE001
                rp.problems.append(f"equivalence check failed to run: {type(exc).__name__}: {str(exc)[:200]}")
            else:
                for variant, cell, old, new in rp.equivalence.diffs[:5]:
                    rp.problems.append(f"equivalence diff [{variant}] {cell}: {old!r} -> {new!r}")
                if len(rp.equivalence.diffs) > 5:
                    rp.problems.append(f"... {len(rp.equivalence.diffs)} equivalence diffs in total")
                if not rp.equivalence.coverage_ok:
                    rp.problems.append("equivalence run had no non-blank calculated cell (vacuous)")
        rp.drift, module_problems = module_check(entry, rp.new_def)
        rp.problems += [f"module check: {p}" for p in module_problems]
    return Plan(rows)


# ── Snapshot and verify ──────────────────────────────────────────────


@dataclass(frozen=True)
class TemplateState:
    code: str
    version: int
    status: str
    ident_hash: str  # every column except definition, modified_by, modified_date
    full_hash: str  # every column
    definition: dict
    modified_by: str | None


@dataclass
class Snapshot:
    row_count: int
    statuses: dict[str, int]
    templates: dict[int, TemplateState]
    worksheets_count: int
    worksheets_hash: str


def snapshot(con: sqlite3.Connection) -> Snapshot:
    """Capture the state ``verify`` compares against."""
    cols = [r[1] for r in con.execute("pragma table_info(test_templates)")]
    skip = {"definition", "modified_by", "modified_date"}
    ident_idx = [i for i, c in enumerate(cols) if c not in skip]
    pos = {c: i for i, c in enumerate(cols)}
    templates: dict[int, TemplateState] = {}
    for row in con.execute("select * from test_templates order by id"):
        templates[row[pos["id"]]] = TemplateState(
            code=row[pos["code"]],
            version=row[pos["version"]],
            status=row[pos["status"]],
            ident_hash=_digest([[row[i] for i in ident_idx]]),
            full_hash=_digest([row]),
            definition=_json(row[pos["definition"]]),
            modified_by=row[pos["modified_by"]],
        )
    statuses = {s: n for s, n in con.execute("select status, count(*) from test_templates group by status")}
    ws_rows = con.execute("select * from test_worksheets order by rowid").fetchall()
    return Snapshot(len(templates), statuses, templates, len(ws_rows), _digest(ws_rows))


def verify(
    con: sqlite3.Connection,
    pre: Snapshot,
    roster: Iterable[RosterEntry] = ROSTER,
    *,
    replay: bool = True,
) -> list[str]:
    """
    Post-state checks against the pre-state snapshot. Returns the failures (an
    empty list means the sync is correct). Safe to call inside the write
    transaction or on a read-only connection.
    """
    roster = tuple(roster)
    failures: list[str] = []
    cur = snapshot(con)
    integrity = [r[0] for r in con.execute("pragma integrity_check")]
    if integrity != ["ok"]:
        failures.append(f"integrity_check: {integrity[:3]}")
    if cur.row_count != pre.row_count:
        failures.append(f"row count {cur.row_count}, was {pre.row_count}")
    if cur.statuses != pre.statuses:
        failures.append(f"status counts {cur.statuses}, were {pre.statuses}")
    if set(cur.templates) != set(pre.templates):
        failures.append("the set of template ids changed")
    if cur.worksheets_count != pre.worksheets_count or cur.worksheets_hash != pre.worksheets_hash:
        failures.append("test_worksheets content changed")

    by_key = {(s.code, s.version): i for i, s in pre.templates.items()}
    roster_ids: set[int] = set()
    worksheets = _load_worksheets(con) if replay else {}
    for entry in roster:
        label = f"{entry.code} v{entry.version}"
        tid = by_key.get((entry.code, entry.version))
        if tid is None or tid not in cur.templates:
            failures.append(f"{label}: not found")
            continue
        roster_ids.add(tid)
        before, after = pre.templates[tid], cur.templates[tid]
        if after.ident_hash != before.ident_hash:
            failures.append(f"{label}: an identity column changed")
        try:
            expected = convert_definition(before.definition, entry.keys)
        except ValueError as exc:
            failures.append(f"{label}: {exc}")
            continue
        if after.definition != expected:
            failures.append(f"{label}: definition is not convert(pre-state definition)")
        if after.definition == before.definition:
            if after.full_hash != before.full_hash:
                failures.append(f"{label}: unchanged definition but the row changed")
        elif after.modified_by != ACTOR:
            failures.append(f"{label}: modified_by is {after.modified_by!r}")
        for key in entry.keys:
            g, g_before = _group(after.definition, key), _group(before.definition, key)
            if g is None or g.get("kind") != "table":
                failures.append(f"{label}: {key} is not a table")
                continue
            if "renderAsTable" in g:
                failures.append(f"{label}: {key} still has renderAsTable")
            if (g_before or {}).get("kind") == "singleton" and (
                g.get("rows") != STANDARD_ROWS or g.get("rowLabel") != STANDARD_ROW_LABEL
            ):
                failures.append(f"{label}: {key} has the wrong rows / rowLabel")
        if entry.code in STANDARD_2_CODES and (_group(after.definition, "standard_2") or {}).get("kind") != "table":
            failures.append(f"{label}: standard_2 is not a table")
        _, module_problems = module_check(entry, after.definition)
        failures += [f"{label}: module check: {p}" for p in module_problems]
        if replay and after.definition != before.definition:
            rep = check_equivalence(before.definition, after.definition, entry.keys, worksheets.get(tid, []))
            if rep.diffs:
                failures.append(f"{label}: {len(rep.diffs)} equivalence diffs, first {rep.diffs[0]!r}")
            if not rep.coverage_ok:
                failures.append(f"{label}: equivalence run was vacuous")

    for tid, before in pre.templates.items():
        if tid in roster_ids or tid not in cur.templates:
            continue
        if cur.templates[tid].full_hash != before.full_hash:
            failures.append(f"{before.code} v{before.version}: not on the roster but changed")
        if before.code == REFERENCE_CODE:
            g = _group(cur.templates[tid].definition, "standard")
            if not g or g.get("kind") != "table" or g.get("rows") != STANDARD_ROWS:
                failures.append(f"{REFERENCE_CODE}: Standard Details is not the reference table")
    return failures


# ── Apply ────────────────────────────────────────────────────────────


@dataclass
class ApplyResult:
    plan: Plan
    backup: Path | None
    updated: list[str]


def _backup(con: sqlite3.Connection, db_path: Path, now: datetime) -> Path:
    dest = db_path.with_name(db_path.name + BACKUP_INFIX + now.strftime("%Y%m%d-%H%M%S"))
    if dest.exists():
        raise RolloutError(f"backup file already exists: {dest}")
    dst = sqlite3.connect(str(dest))
    try:
        con.backup(dst)
    finally:
        dst.close()
    check = _open_ro(dest)
    try:
        want = con.execute("select count(*) from test_templates").fetchone()[0]
        got = check.execute("select count(*) from test_templates").fetchone()[0]
        integrity = [r[0] for r in check.execute("pragma integrity_check")]
    finally:
        check.close()
    if got != want or integrity != ["ok"]:
        raise RolloutError(f"backup {dest} failed its check ({got} rows, expected {want}; integrity {integrity[:3]})")
    return dest


def apply_changes(
    db_path: str | Path,
    roster: Iterable[RosterEntry] = ROSTER,
    *,
    expected_rows: int = EXPECTED_ROWS,
    expected_statuses: dict[str, int] | None = None,
    now: datetime | None = None,
    replay: bool = True,
) -> ApplyResult:
    """
    Write the converted definitions: fingerprint, plan, backup, then one
    ``BEGIN IMMEDIATE`` transaction that updates only ``definition``,
    ``modified_by`` and ``modified_date``, verifies inside the transaction and
    commits. Any failure raises ``RolloutError`` after a rollback. When every row
    is already converted nothing is written and no backup is taken.
    """
    roster = tuple(roster)
    db_path = Path(db_path)
    now = now or datetime.now(timezone.utc)
    con = sqlite3.connect(str(db_path), timeout=LOCK_TIMEOUT_S, isolation_level=None)
    try:
        fingerprint(con, expected_rows, expected_statuses)
        plan = plan_changes(con, roster)
        if not plan.ok:
            raise RolloutError("plan has problems, nothing written:\n  " + "\n  ".join(plan.problems))
        todo = plan.to_convert
        if not todo:
            return ApplyResult(plan, None, [])
        backup = _backup(con, db_path, now)
        con.execute("BEGIN IMMEDIATE")
        try:
            pre = snapshot(con)
            for rp in todo:
                stored = con.execute("select definition from test_templates where id=?", (rp.row_id,)).fetchone()
                if stored is None or _json(stored[0]) != rp.old_def:
                    raise RolloutError(f"{rp.entry.code}: definition changed since it was planned")
            stamp = now.strftime(_TS_FORMAT)
            for rp in todo:
                cur = con.execute(
                    "UPDATE test_templates SET definition=?, modified_by=?, modified_date=? WHERE id=?",
                    (json.dumps(rp.new_def), ACTOR, stamp, rp.row_id),
                )
                if cur.rowcount != 1:
                    raise RolloutError(f"{rp.entry.code}: expected one updated row, got {cur.rowcount}")
            failures = verify(con, pre, roster, replay=replay)
            if failures:
                raise RolloutError("verification failed inside the transaction:\n  " + "\n  ".join(failures))
            con.execute("COMMIT")
        except BaseException:
            if con.in_transaction:
                con.execute("ROLLBACK")
            raise
        return ApplyResult(plan, backup, [f"{rp.entry.code} v{rp.entry.version}" for rp in todo])
    finally:
        con.close()


# ── Report ───────────────────────────────────────────────────────────


def write_roster(plan: Plan, path: Path, header: Iterable[str] = ()) -> None:
    """Write the per-row roster table (``roster.md``)."""
    lines = ["# Standard Details to tabular: roster", ""]
    lines += list(header)
    lines += [
        "",
        f"Rows to convert: {len(plan.to_convert)} of {len(plan.rows)}; groups converted: {plan.group_count}; "
        f"reference-audit violations: {plan.audit_violations}; equivalence diffs: {plan.equivalence_diffs}; "
        f"problems: {len(plan.problems)}.",
        "",
        "| Code | Id | Ver | Status | Groups | Source | Module | Action | Drift | Equivalence variants | Non-blank calculated |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in plan.rows:
        e = r.entry
        variants = (
            ", ".join(f"{k} {n}" for k, n in Counter(r.equivalence.variants).items()) if r.equivalence else "-"
        )
        coverage = str(r.equivalence.nonblank_calculated) if r.equivalence else "-"
        lines.append(
            f"| {e.code} | {r.row_id if r.row_id is not None else '-'} | {e.version} | {r.status or '-'} "
            f"| {', '.join(e.keys)} | {e.source} | {e.module} | {r.action} "
            f"| {', '.join(r.drift) or '-'} | {variants} | {coverage} |"
        )
    if plan.problems:
        lines += ["", "## Problems", ""] + [f"- {p}" for p in plan.problems]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary(plan: Plan) -> str:
    skipped = sum(1 for r in plan.rows if r.action == "skip")
    drifted = sum(1 for r in plan.rows if r.entry.module == "drifted")
    return (
        f"rows to convert: {len(plan.to_convert)} (already tabular: {skipped}), groups: {plan.group_count}\n"
        f"reference-audit violations: {plan.audit_violations}\n"
        f"equivalence diffs: {plan.equivalence_diffs}\n"
        f"module drift: {drifted} rows drifted, "
        f"{sum(1 for r in plan.rows if r.entry.module == 'none')} DB-only, "
        f"{sum(1 for r in plan.rows if r.entry.module == 'equal')} equal to their module\n"
        f"problems: {len(plan.problems)}"
    )


def _latest_backup(db_path: Path) -> Path | None:
    found = sorted(db_path.parent.glob(db_path.name + BACKUP_INFIX + "*"))
    return found[-1] if found else None


# ── CLI ──────────────────────────────────────────────────────────────


def main(
    argv: list[str] | None = None,
    *,
    roster: Iterable[RosterEntry] = ROSTER,
    expected_rows: int = EXPECTED_ROWS,
    expected_statuses: dict[str, int] | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="standard_tabular_rollout", description=__doc__.splitlines()[0])
    parser.add_argument("--db", required=True, help="absolute path to lims.db")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="plan and prove equivalence, read-only")
    mode.add_argument("--apply", action="store_true", help="back up, then write the converted definitions")
    mode.add_argument("--verify", action="store_true", help="check the live state against the latest backup, read-only")
    parser.add_argument("--report-dir", default=".", help="where roster.md is written")
    parser.add_argument("--backup", help="pre-state backup for --verify (default: newest beside the database)")
    args = parser.parse_args(argv)
    roster = tuple(roster)
    db_path = Path(args.db)
    roster_path = Path(args.report_dir) / "roster.md"
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        if args.dry_run:
            con = _open_ro(db_path)
            try:
                fp = fingerprint(con, expected_rows, expected_statuses)
                plan = plan_changes(con, roster)
            finally:
                con.close()
            write_roster(plan, roster_path, [f"Mode: dry-run, {when}. Database: `{db_path}`. Fingerprint: {fp}."])
            print(_summary(plan))
            for p in plan.problems:
                print("PROBLEM:", p)
            print(f"roster: {roster_path}")
            return 0 if plan.ok else 1

        if args.apply:
            result = apply_changes(
                db_path, roster, expected_rows=expected_rows, expected_statuses=expected_statuses
            )
            print(_summary(result.plan))
            if not result.updated:
                print("no changes: every roster group is already tabular; nothing written")
                return 0
            write_roster(
                result.plan,
                roster_path,
                [f"Mode: apply, {when}. Database: `{db_path}`. Backup: `{result.backup}`."],
            )
            print(f"updated {len(result.updated)} rows; backup: {result.backup}")
            print(f"roster: {roster_path}")
            return 0

        backup = Path(args.backup) if args.backup else _latest_backup(db_path)
        if backup is None or not backup.exists():
            raise RolloutError("no pre-state backup found; pass --backup")
        pre_con = _open_ro(backup)
        try:
            pre = snapshot(pre_con)
            plan = plan_changes(pre_con, roster)
        finally:
            pre_con.close()
        con = _open_ro(db_path)
        try:
            fingerprint(con, expected_rows, expected_statuses)
            failures = verify(con, pre, roster)
        finally:
            con.close()
        write_roster(
            plan,
            roster_path,
            [f"Mode: verify, {when}. Database: `{db_path}`. Pre-state backup: `{backup}`."]
            + ([f"VERIFY FAILED: {len(failures)} failures"] if failures else ["Verify: all checks passed."]),
        )
        print(_summary(plan))
        for f in failures:
            print("FAIL:", f)
        print("verify:", "FAILED" if failures else "OK", f"(pre-state backup {backup})")
        print(f"roster: {roster_path}")
        return 1 if failures or not plan.ok else 0
    except RolloutError as exc:
        print(f"ABORTED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
