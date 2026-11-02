"""
Seed the ARD-EXP-TEMPLATES master from the extracted ADS sheets.

Creates one row per ADS sheet (53 total), preserving the COMPLETE, non-standardised
content of every sheet:
  - template_code  : e.g. "ADS-01-00"  (source form id)
  - document_no    : e.g. "ADS/001/00" (the sheet's own ADS No.)
  - template_name  : "ADS-01-00 — Standard: Description / Solubility / ..." (descriptive)
  - module         : "ARD"
  - comments       : short human summary (category, #sections, primary tests)
  - content        : the full extracted structure for the sheet as JSON text
                     (header table + every section/table, verbatim)
  - is_active      : True

Idempotent: adds any missing columns to an existing table, and upserts by
template_code so re-running refreshes content without creating duplicates.

Run from backend-v2:  python scripts/seed_ads_exp_templates.py
"""
import json
import os
import sqlite3
from datetime import datetime, timezone

DB = os.path.join(os.path.dirname(__file__), "..", "lims.db")
DUMP = r"D:\eLN-ARD-templates\TRF-eLn-ARD\_dump\_all.json"
CLASSIFY = r"D:\eLN-ARD-templates\TRF-eLn-ARD\_dump\_classify.json"

# Default metadata applied to every seeded ADS template.
MODULE = "eLN ARD"
PLANT = "API"
LOCATION = "Hinjewadi"

HEADER_SHORT = {
    "Name of Standard": "Standard",
    "Name of Raw Material": "Raw Material",
    "Name of Product": "Product",
    "Name of Solution": "Solution",
    "Name of Intermediate": "Intermediate",
    "Name of Product / IM": "Product / Intermediate",
    "Batch No.": "Batch",
    "Date": "Water / Purified Water",
    "(unknown)": "Analytical Data Sheet",
}


def ensure_columns(cur):
    cur.execute("PRAGMA table_info(ard_exp_templates)")
    cols = {r[1] for r in cur.fetchall()}
    to_add = {
        "template_code": "VARCHAR(100)",
        "document_no": "VARCHAR(100)",
        "content": "TEXT",
    }
    for name, decl in to_add.items():
        if name not in cols:
            cur.execute(f"ALTER TABLE ard_exp_templates ADD COLUMN {name} {decl}")
            print(f"  + added column {name}")


def primary_tests(sections):
    """The non-'Description' test titles that define what the sheet does."""
    titles = [s["title"] for s in sections if s["title"].lower() != "description"]
    # drop the repetitive 'Transferred ... Observation' solubility sub-lines
    titles = [t for t in titles if not t.lower().startswith("transferred")]
    return titles


def build_name(code, cat_short, sections):
    tests = primary_tests(sections)
    if tests:
        head = " / ".join(tests[:3])
        if len(tests) > 3:
            head += f" (+{len(tests) - 3} more)"
    else:
        head = "General data sheet"
    return f"{code} — {cat_short}: {head}"[:500]


def build_comments(cat_short, doc_no, sections):
    tests = primary_tests(sections)
    n = len(sections)
    summary = ", ".join(t for t in tests[:6]) if tests else "general / free-form data sheet"
    return (
        f"{cat_short} analytical data sheet ({doc_no}). "
        f"{n} section(s). Tests: {summary}."
    )[:2000]


def main():
    with open(DUMP, encoding="utf-8") as fh:
        dump = json.load(fh)
    with open(CLASSIFY, encoding="utf-8") as fh:
        classify = json.load(fh)

    con = sqlite3.connect(DB)
    cur = con.cursor()
    ensure_columns(cur)

    now = datetime.now(timezone.utc).isoformat()
    created = 0
    updated = 0

    for code in sorted(dump.keys()):
        meta = classify.get(code, {})
        cat = meta.get("header_category", "(unknown)")
        cat_short = HEADER_SHORT.get(cat, cat)
        doc_no = meta.get("ads_no", "") or ""
        sections = meta.get("sections", [])

        name = build_name(code, cat_short, sections)
        comments = build_comments(cat_short, doc_no, sections)
        # Full verbatim content: the complete block list for this sheet, plus
        # the derived header/section index, so nothing from the sheet is lost.
        content_obj = {
            "source_form": code,
            "document_no": doc_no,
            "header_category": cat,
            "sections_index": sections,
            "blocks": dump[code],
        }
        content = json.dumps(content_obj, ensure_ascii=False)

        cur.execute("SELECT id FROM ard_exp_templates WHERE template_code = ?", (code,))
        existing = cur.fetchone()
        if existing:
            cur.execute(
                """UPDATE ard_exp_templates SET template_name=?, comments=?, module=?,
                   plant=?, location=?, is_active=1, document_no=?, content=?,
                   modified_by=?, modified_date=?
                   WHERE template_code=?""",
                (name, comments, MODULE, PLANT, LOCATION, doc_no, content, "seed:ads", now, code),
            )
            updated += 1
        else:
            cur.execute(
                """INSERT INTO ard_exp_templates
                   (template_name, comments, primary_department, plant, location,
                    is_active, secondary_department, module, template_code, document_no,
                    content, created_by, created_date, modified_by, modified_date)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, comments, None, PLANT, LOCATION, 1, None, MODULE, code, doc_no,
                 content, "seed:ads", now, "seed:ads", now),
            )
            created += 1

    con.commit()
    cur.execute("SELECT COUNT(*) FROM ard_exp_templates")
    total = cur.fetchone()[0]
    con.close()
    print(f"Seed complete. created={created} updated={updated} total_rows={total}")


if __name__ == "__main__":
    main()
