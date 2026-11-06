"""Exploration prototype (read-only on the DB): convert every in-scope live definition
with the planned transform and compare old vs new evaluation. NOT shipped; the real
harness is scripts/standard_tabular_rollout.py. Run from the worktree backend-v2.
"""
import copy, json, sqlite3, sys
sys.path.insert(0, ".")
from src.domain.services.calculation import expression as ex
from src.domain.services.calculation import evaluator as ev
from src.domain.services.calculation.evaluator import WorksheetEvaluator
from src.domain.services.calculation.template_schema import TemplateDefinition

SINK = "--sink" in sys.argv
if SINK:
    orig = ev.evaluate
    def patched(expr, scope):
        v = orig(expr, scope)
        if isinstance(v, ex.ColumnSeries):
            v = v[0] if len(v) else ex.EMPTY
        return v
    ev.evaluate = patched  # prototype of the planned sink collapse (field + criteria)

KEYS = ("standard", "standard_2")
ROWS = {"min": 1, "max": 10, "default": 1}


def convert(d):
    d = copy.deepcopy(d)
    for g in d["groups"]:
        if g["key"] in KEYS and g["kind"] == "singleton":
            g["kind"] = "table"; g["rows"] = dict(ROWS); g["rowLabel"] = {"format": "STD - {n}"}
            g.pop("renderAsTable", None)
    return d


def synth(d, pad=False):
    n = [0]
    def val(f):
        n[0] += 1
        t = f.get("type")
        if t == "text": return "S"
        if t == "date": return "2026-01-01"
        if f.get("options"): return f["options"][0] if not isinstance(f["options"][0], dict) else f["options"][0].get("value")
        if f.get("default") is not None and n[0] % 3 == 0: return f["default"]
        return round(1.5 + ((n[0] * 7919) % 5000) / 100.0, 3)
    ctx = {}
    for c in d.get("context", []):
        ctx[c["key"]] = c["default"] if c.get("default") is not None else (val(c) if c.get("type") != "text" else "T")
    grp = {}
    for g in d["groups"]:
        rows_n = 1 if g["kind"] == "singleton" else g.get("rows", {}).get("default", 1)
        if pad and g["key"] in KEYS: rows_n = 3
        grp[g["key"]] = [{f["key"]: val(f) for f in g["fields"] if f["kind"] in ("input", "area")} for _ in range(rows_n)]
    return ctx, grp


def flat(res, converted_keys):
    cells = {}
    for k, v in res.values.items():
        if "." in k and k.split(".")[0] in converted_keys: continue
        cells["v:" + k] = v
    for gk, rows in res.rows.items():
        for i, r in enumerate(rows):
            for fk, v in r.items():
                cells[f"r:{gk}[{i}].{fk}"] = v
    for c in res.criteria:
        cells["c:" + c.key] = (c.observed, c.passed)
    cells["reportable"] = res.reportable_result
    return cells


con = sqlite3.connect("file:d:/RD-instance/GIT/backend-v2/lims.db?mode=ro", uri=True)
bad = 0
wsrows = con.execute("select template_id,context_values,group_values from test_worksheets").fetchall()
for id_, code, ver, status, dfn in con.execute("select id,code,version,status,definition from test_templates where status in ('Active','Draft') order by code"):
    old = json.loads(dfn)
    if not any(g["key"] in KEYS and g["kind"] == "singleton" for g in old["groups"]):
        continue
    new = convert(old)
    try:
        po = TemplateDefinition.parse(old); pn = TemplateDefinition.parse(new)
        WorksheetEvaluator(pn).evaluate({}, {})
    except Exception as e:
        print("PARSE/VALIDATE FAIL", code, e); bad += 1; continue
    ck = {g["key"] for g in old["groups"] if g["key"] in KEYS and g["kind"] == "singleton"}
    variants = [("empty", {}, {})]
    c, g = synth(old); variants.append(("synth", c, g))
    for t, cv, gv in wsrows:
        if t == id_:
            variants.append(("ws", json.loads(cv) if cv else {}, json.loads(gv) if gv else {}))
    diffs = []; nonblank = 0
    for name, c, g in variants:
        try:
            ro = WorksheetEvaluator(po).evaluate(c, g)
        except Exception as e:
            diffs.append((name, "OLD-EVAL-ERR " + str(e)[:80])); continue
        try:
            rn = WorksheetEvaluator(pn).evaluate(c, g)
        except Exception as e:
            diffs.append((name, "NEW-EVAL-ERR " + str(e)[:80])); continue
        fo, fn = flat(ro, ck), flat(rn, ck)
        if name == "synth":
            nonblank = sum(1 for k, v in fo.items() if k.startswith("r:") and v is not ex.EMPTY and v is not None and v != "")
        # old standard rows -> new standard rows identical
        for k in set(fo) | set(fn):
            a, b = fo.get(k, "<missing>"), fn.get(k, "<missing>")
            if a is ex.EMPTY and b is ex.EMPTY: continue
            if a != b: diffs.append((name, k, a, b))
    # padded (3 std rows) variant: everything outside std rows must equal old 1-row synth
    c, g = synth(old); ro = WorksheetEvaluator(po).evaluate(c, g)
    gp = {k: [dict(r) for r in v] for k, v in g.items()}
    for k in ck:
        gp[k] = gp[k] + [{f: (x * 1.37 if isinstance(x, (int, float)) else x) for f, x in gp[k][0].items()} for _ in range(2)]
    rp = WorksheetEvaluator(pn).evaluate(c, gp)
    fo, fp = flat(ro, ck), flat(rp, ck)
    for k in fo:
        if any(k.startswith(f"r:{x}[") for x in ck): continue
        a, b = fo[k], fp.get(k, "<missing>")
        if a is ex.EMPTY and b is ex.EMPTY: continue
        if a != b: diffs.append(("pad3", k, a, b))
    print(f"{code} v{ver} {status:6} groups={sorted(ck)} variants={len(variants)} nonblank_rows_cells={nonblank} diffs={len(diffs)}")
    for d_ in diffs[:6]: print("     ", d_)
    bad += bool(diffs)
print("TEMPLATES WITH DIFFS:", bad, "SINK" if SINK else "NO-SINK")
