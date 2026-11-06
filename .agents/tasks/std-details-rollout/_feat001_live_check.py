"""Ad-hoc read-only check of the FEAT-001 harness against the live catalogue."""
import json, sqlite3, sys
sys.path.insert(0, ".")
from scripts.standard_tabular_rollout import ROSTER, convert_definition, audit_references, check_equivalence

con = sqlite3.connect("file:d:/RD-instance/GIT/backend-v2/lims.db?mode=ro", uri=True)
ws = {}
for t, c, g in con.execute("select template_id, context_values, group_values from test_worksheets"):
    ws.setdefault(t, []).append((json.loads(c) if c else {}, json.loads(g) if g else {}))
tot_diffs = tot_viol = nocov = 0
for e in ROSTER:
    row = con.execute("select id, code, version, status, definition from test_templates where code=? and version=?", (e.code, e.version)).fetchone()
    assert row, e
    assert (row[0], row[3]) == (e.template_id, e.status), (e, row[:4])
    old = json.loads(row[4])
    viol = audit_references(old, e.keys)
    new = convert_definition(old, e.keys)
    rep = check_equivalence(old, new, e.keys, ws.get(e.template_id, []))
    tot_viol += len(viol); tot_diffs += len(rep.diffs); nocov += (not rep.coverage_ok)
    print(f"{e.code} v{e.version} viol={len(viol)} variants={len(rep.variants)} nonblank_calc={rep.nonblank_calculated} reportable={rep.reportable!r} diffs={len(rep.diffs)}")
    for v in viol[:3]: print("    V", v)
    for d in rep.diffs[:4]: print("    D", d)
print("TOTAL violations", tot_viol, "diffs", tot_diffs, "no-coverage", nocov, "rows", len(ROSTER))
