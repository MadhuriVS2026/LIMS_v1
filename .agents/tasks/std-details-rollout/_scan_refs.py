"""Exploration scan (read-only): how does every in-scope definition reference the
`standard` / `standard_2` groups from OUTSIDE those groups? Classifies each ref by
its AST parent so we know whether a bare multi-row ColumnSeries could change a value.
Run from backend-v2:  python <this file> [db_path]
"""
import json, re, sqlite3, sys
from collections import Counter, defaultdict

sys.path.insert(0, ".")
from src.domain.services.calculation import expression as ex

DB = sys.argv[1] if len(sys.argv) > 1 else r"d:/RD-instance/GIT/backend-v2/lims.db"
TARGET = {"standard", "standard_2"}
COERCING = {"round", "trunc", "abs", "sqrt", "ln", "log10", "exp"}  # arg goes via _as_number
rx = re.compile(r"\bstandard(_2)?\b")


def classify(node, parent, idx, out, top):
    if isinstance(node, ex._Ref):
        head = node.parts[0] if node.parts else None
        if head in TARGET:
            has_index = len(node.parts) > 2 and not isinstance(node.parts[2], str)
            if len(node.parts) == 1:
                kind = "WHOLE-GROUP"
            elif parent is None:
                kind = "HAZARD:top-level-bare"
            elif isinstance(parent, ex._Binary):
                kind = "ok:binary-" + ("logic" if parent.op in ("and", "or") else "arith/cmp")
                if parent.op in ("and", "or"):
                    kind = "HAZARD:logic"
            elif isinstance(parent, ex._Unary):
                kind = "HAZARD:not" if parent.op == "not" else "ok:unary"
            elif isinstance(parent, ex._Call):
                if parent.name in COERCING:
                    kind = "ok:coercing-fn-" + parent.name
                elif parent.name == "if" and idx == 0:
                    kind = "HAZARD:if-cond"
                else:
                    kind = f"HAZARD:fn-{parent.name}[{idx}]"
            else:
                kind = "HAZARD:" + type(parent).__name__
            if has_index:
                kind = "ok:explicit-index"
            out.append((kind, ".".join(str(p) for p in node.parts if isinstance(p, str))))
        return
    if isinstance(node, ex._Unary):
        classify(node.operand, node, 0, out, top)
    elif isinstance(node, ex._Binary):
        classify(node.left, node, 0, out, top)
        classify(node.right, node, 1, out, top)
    elif isinstance(node, ex._Call):
        for i, a in enumerate(node.args):
            classify(a, node, i, out, top)
    elif isinstance(node, ex._ListNode):
        for i, a in enumerate(node.items):
            classify(a, node, i, out, top)


def walk(obj, path, group_key, hits):
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk(v, path + [k], group_key, hits)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, path + [i], group_key, hits)
    elif isinstance(obj, str) and rx.search(obj):
        if path and path[-1] in ("label", "limitText", "help", "description", "key", "unit"):
            return
        hits.append((".".join(map(str, path)), obj))


con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
summary = defaultdict(Counter)
for id_, code, ver, status, definition in con.execute(
    "select id, code, version, status, definition from test_templates order by code, version"
):
    if status not in ("Active", "Draft"):
        continue
    d = json.loads(definition)
    keys = {g["key"] for g in d["groups"]}
    if not (keys & TARGET):
        continue
    for g in d["groups"]:
        hits = []
        # Skip the target group's own fields (bare names resolve in-row there)
        if g["key"] in TARGET:
            continue
        walk(g, ["groups", g["key"]], g["key"], hits)
        for p, s in hits:
            try:
                node = ex._parse(s)
            except Exception:
                summary[code]["unparsed:" + p.rsplit(".", 1)[-1]] += 1
                print("UNPARSED", code, p, s[:120])
                continue
            out = []
            classify(node, None, 0, out, True)
            for kind, ref in out:
                summary[code][kind] += 1
                if kind.startswith("HAZARD") or kind.startswith("WHOLE"):
                    print(kind, code, p, "::", s[:160])
    hits = []
    for top in ("criteria", "resultRef", "context", "chart", "summary"):
        if top in d:
            walk(d[top], [top], None, hits)
    for p, s in hits:
        try:
            node = ex._parse(s)
        except Exception:
            print("UNPARSED-TOP", code, p, s[:120])
            summary[code]["unparsed-top"] += 1
            continue
        out = []
        classify(node, None, 0, out, True)
        for kind, ref in out:
            summary[code]["top:" + kind] += 1
            print("TOP", kind, code, p, "::", s[:160])
for code, c in summary.items():
    print(code, dict(c))
