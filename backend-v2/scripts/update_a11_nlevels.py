"""Branch the three A11 templates to DRAFTs with variable (N<=10) dose levels.

The A11 microbial-bioassay standard dose-level design was a fixed five rows. This
change raises the ceiling to ten (rows min 3 / max 10 / default 5) on every table
index-locked to the dose-level count, and makes the reference-row index N-safe,
while keeping every existing 5-level worksheet's results bit-for-bit identical.
The module `scripts.template_definitions.a11_microbial_bioassay` already carries
the updated definitions (parity-tested in tests/calculation).

An Active template is immutable, so the audited route (same as
update_a11_0001_std_stock_table.py / update_a6a5_v3_definition.py) is used for all
three codes:

  1. backs up backend-v2/lims.db to lims.db.bak-a11nlevels-<UTC timestamp>
     (gitignored convention) BEFORE any API write,
  2. logs in to the local API (admin/admin123),
  3. for each code resolves the live Active row and finds-or-branches an
     unapproved Draft of the next version (idempotent re-runs),
  4. PUTs the module definition onto that Draft (server re-validates), and
  5. GETs the Draft back and prints a PASS/FAIL verification summary.

TPL-A11-0001 special case: a prior task already created an unapproved v2 Draft
(id 55). This script reuses that Draft and PUTs the new definition onto it rather
than branching a v3 on top of an unapproved Draft.

It NEVER calls /submit or /approve — every Draft is left for a human to approve.

HOW TO RUN (NOT run as part of this code change — the apply-live step runs it)
  1. Start the backend as start-lims.bat does:
         cd /d d:\\RD-instance\\GIT\\backend-v2
         python -m uvicorn src.main:app --host 127.0.0.1 --port 8443
     (or run d:\\RD-instance\\GIT\\start-lims.bat, which also starts the frontend).
  2. From d:\\RD-instance\\GIT\\backend-v2:
         python -m scripts.update_a11_nlevels
Exit code 0 = all checks PASS, 1 = any FAIL / API error.
"""
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

from scripts.template_definitions.a11_microbial_bioassay import (
    A11_AMPHO_API_DEFINITION,
    A11_API_DEFINITION,
    A11_FP_DEFINITION,
)

BASE = "http://127.0.0.1:8443/api/v1"
DB_PATH = Path(__file__).resolve().parent.parent / "lims.db"

_EXPECTED_ROWS = {"min": 3, "max": 10, "default": 5}

#  TPL-A11-0001 has a pre-existing unapproved v2 Draft from the prior task; reuse
#  it instead of branching a new version on top of a Draft.
_A11_0001_KNOWN_DRAFT_ID = 55

#  Per code: the definition to push, and which dose-level-coupled tables to verify
#  carry the new rows bound. A11-0003 only ships the std_stock table.
_PLAN = [
    {
        "code": "TPL-A11-0001",
        "definition": A11_API_DEFINITION,
        "rows_tables": ("std_stock", "standard"),
        "known_draft_id": _A11_0001_KNOWN_DRAFT_ID,
    },
    {
        "code": "TPL-A11-0002",
        "definition": A11_FP_DEFINITION,
        "rows_tables": ("standard",),  # FP keeps std_stock a singleton
        "known_draft_id": None,
    },
    {
        "code": "TPL-A11-0003",
        "definition": A11_AMPHO_API_DEFINITION,
        "rows_tables": ("std_stock",),  # stock-only worksheet, no standard group
        "known_draft_id": None,
    },
]


def _backup_db() -> Path | None:
    if not DB_PATH.exists():
        print(f"WARNING: {DB_PATH} not found; no backup taken")
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = DB_PATH.with_name(f"lims.db.bak-a11nlevels-{stamp}")
    shutil.copy2(DB_PATH, dest)
    print(f"database backup: {dest}")
    return dest


def _login() -> str:
    r = requests.post(
        f"{BASE}/auth/login",
        data={"username": "admin", "password": "admin123"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"    [{mark}] {label}{(' - ' + detail) if detail else ''}")
    return ok


def _rows_ok(group: dict) -> bool:
    rows = group.get("rows") or {}
    return all(rows.get(k) == v for k, v in _EXPECTED_ROWS.items())


def _resolve_active(h: dict, code: str) -> dict | None:
    """The live Active row for a code, via the summary list."""
    r = requests.get(
        f"{BASE}/test-templates", headers=h, params={"status": "Active"}, timeout=15
    )
    r.raise_for_status()
    return next((t for t in r.json() if t.get("code") == code), None)


def _resolve_any_by_code(h: dict, code: str) -> list[dict]:
    """Every version row for a code (any status)."""
    r = requests.get(f"{BASE}/test-templates", headers=h, timeout=15)
    r.raise_for_status()
    return [t for t in r.json() if t.get("code") == code]


def _find_or_branch_draft(h: dict, code: str, known_draft_id: int | None) -> tuple[int, int] | None:
    """Return (draft_id, draft_version), reusing an existing unapproved Draft or
    branching a fresh one from the live Active row. None on resolution failure."""
    #  Reuse a known Draft id (TPL-A11-0001 v2) if it is still an unapproved Draft.
    if known_draft_id is not None:
        r = requests.get(f"{BASE}/test-templates/{known_draft_id}", headers=h, timeout=15)
        if r.status_code < 400:
            row = r.json()
            if row.get("code") == code and row.get("status") == "Draft":
                print(f"  reusing known Draft: id={known_draft_id} v{row['version']}")
                return known_draft_id, row["version"]
            print(
                f"  known Draft id={known_draft_id} is {row.get('status')} "
                f"(code {row.get('code')}); falling back to code resolution"
            )

    active = _resolve_active(h, code)
    if active is None:
        print(f"  ERROR: no Active template for {code}")
        return None
    base_id = active["id"]
    next_version = active["version"] + 1
    print(f"  base Active: id={base_id} v{active['version']} status={active['status']}")

    #  Reuse an existing unapproved Draft of the next version if one exists.
    r = requests.get(f"{BASE}/test-templates/{base_id}/versions", headers=h, timeout=15)
    r.raise_for_status()
    draft = next(
        (v for v in r.json() if v.get("version") == next_version and v.get("status") == "Draft"),
        None,
    )
    if draft is not None:
        print(f"  reusing existing v{next_version} Draft: id={draft['id']}")
        return draft["id"], draft["version"]

    r = requests.post(f"{BASE}/test-templates/{base_id}/new-version", headers=h, timeout=15)
    r.raise_for_status()
    new_ver = r.json()
    print(f"  branched v{new_ver['version']} Draft: id={new_ver['id']} status={new_ver['status']}")
    return new_ver["id"], new_ver["version"]


def _process(h: dict, item: dict) -> tuple[bool, str]:
    code = item["code"]
    print(f"\n=== {code} ===")
    resolved = _find_or_branch_draft(h, code, item["known_draft_id"])
    if resolved is None:
        return False, f"{code}: unresolved"
    draft_id, draft_version = resolved

    #  Capture the live Active definition for the "unchanged" comparisons.
    active = _resolve_active(h, code)
    base_def = None
    if active is not None:
        r = requests.get(f"{BASE}/test-templates/{active['id']}", headers=h, timeout=15)
        if r.status_code < 400:
            base_def = r.json()["definition"]

    r = requests.put(
        f"{BASE}/test-templates/{draft_id}/definition",
        headers=h,
        json={"definition": item["definition"]},
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"  ERROR: definition PUT rejected ({r.status_code}): {r.text[:500]}")
        return False, f"{code}: PUT rejected"
    print(f"  definition PUT accepted ({r.status_code})")

    r = requests.get(f"{BASE}/test-templates/{draft_id}", headers=h, timeout=15)
    r.raise_for_status()
    stored = r.json()
    definition = stored["definition"]
    groups = {g["key"]: g for g in definition["groups"]}

    print(f"  Draft verification (id={draft_id} v{stored['version']}):")
    ok = True
    ok &= _check("status == Draft (not approved)", stored["status"] == "Draft", stored["status"])
    for key in item["rows_tables"]:
        grp = groups.get(key)
        ok &= _check(
            f"{key}.rows == min3/max10/default5",
            grp is not None and _rows_ok(grp),
            str(grp.get("rows") if grp else None),
        )
    #  resultRef + criteria must be unchanged versus the live Active definition.
    if base_def is not None:
        ok &= _check(
            "resultRef unchanged vs live Active",
            definition.get("resultRef") == base_def.get("resultRef"),
            str(definition.get("resultRef")),
        )
        ok &= _check(
            "criteria unchanged vs live Active",
            definition.get("criteria") == base_def.get("criteria"),
        )
    else:
        print("    [WARN] no live Active definition to diff resultRef/criteria against")

    #  The curve aggregates must still be present (N-aware by construction).
    if "curve" in groups:
        cfields = {f["key"]: f for f in groups["curve"]["fields"]}
        for fk in ("ref_grand", "curve_slope", "curve_intercept", "r_squared"):
            ok &= _check(f"curve.{fk} present", fk in cfields)
    else:
        print("    [note] no curve group in this template (stock-only worksheet)")

    return ok, f"{code}: v{draft_version} id={draft_id} {'PASS' if ok else 'FAIL'}"


def main() -> int:
    _backup_db()
    token = _login()
    h = {"Authorization": f"Bearer {token}"}

    overall = True
    summaries: list[str] = []
    for item in _PLAN:
        ok, summary = _process(h, item)
        overall &= ok
        summaries.append(summary)

    print("\n" + "=" * 60)
    print("Per-code result (all left as DRAFT, never submitted/approved):")
    for s in summaries:
        print(f"  {s}")
    print(f"\n{'OVERALL: PASS' if overall else 'OVERALL: FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
