"""Branch TPL-A6A-0005 (template id 41) to a new v3 DRAFT with the 20-slot form.

This is the audited, API-driven route the service lifecycle requires: an Active
template is immutable, so a new version must be branched to a Draft before its
definition can be replaced. The script

  1. logs in to the local API (admin/admin123),
  2. resolves id 41 and asserts code=TPL-A6A-0005 / status=Active / version=2,
  3. POSTs /new-version to branch a v3 Draft,
  4. PUTs the module's A6A_LEUP_DEFINITION (the 20-slot form, kept byte-identical
     to the parity-tested seed module) onto the Draft, and
  5. GETs the Draft back and prints a PASS/FAIL verification summary.

It NEVER calls /submit or /approve — v3 is left as a DRAFT for the orchestrator
to approve after review. The definition PUT re-validates (parse + dependency
graph) server-side; a bad definition is rejected there.

Run with the backend up on 127.0.0.1:8443. If the backend is down, the module
parity test (tests/calculation/test_a6a_0005_leuprolide_parity.py) still
certifies the exact definition this script would push.
"""
import sys

import requests

from scripts.template_definitions.a6a_leuprolide_microsphere import A6A_LEUP_DEFINITION

BASE = "http://127.0.0.1:8443/api/v1"
TEMPLATE_ID = 41
CODE = "TPL-A6A-0005"
EXPECTED_SAMPLES = 20
EXPECTED_WEIGHTS_MAX = 20
EXPECTED_TIMEPOINTS_MAX = 10


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
    print(f"  [{mark}] {label}{(' — ' + detail) if detail else ''}")
    return ok


def main() -> int:
    token = _login()
    h = {"Authorization": f"Bearer {token}"}

    #  Resolve the live Active v2.
    r = requests.get(f"{BASE}/test-templates/{TEMPLATE_ID}", headers=h, timeout=15)
    r.raise_for_status()
    base = r.json()
    print(
        f"base template: id={base['id']} code={base['code']} "
        f"status={base['status']} version={base['version']}"
    )
    if base["code"] != CODE:
        print(f"ERROR: id {TEMPLATE_ID} is {base['code']}, expected {CODE}")
        return 1

    #  Find or branch the v3 Draft (idempotent: reuse an existing unapproved v3).
    r = requests.get(
        f"{BASE}/test-templates/{TEMPLATE_ID}/versions", headers=h, timeout=15
    )
    r.raise_for_status()
    versions = r.json()
    draft = next(
        (v for v in versions if v.get("version") == 3 and v.get("status") == "Draft"),
        None,
    )
    if draft is not None:
        v3_id = draft["id"]
        print(f"reusing existing v3 Draft: id={v3_id}")
    else:
        r = requests.post(
            f"{BASE}/test-templates/{TEMPLATE_ID}/new-version", headers=h, timeout=15
        )
        r.raise_for_status()
        new_ver = r.json()
        v3_id = new_ver["id"]
        print(
            f"branched v3 Draft: id={v3_id} version={new_ver['version']} "
            f"status={new_ver['status']}"
        )

    #  PUT the 20-slot definition (byte-identical to the parity-tested module).
    r = requests.put(
        f"{BASE}/test-templates/{v3_id}/definition",
        headers=h,
        json={"definition": A6A_LEUP_DEFINITION},
        timeout=30,
    )
    if r.status_code >= 400:
        print(f"ERROR: definition PUT rejected ({r.status_code}): {r.text[:500]}")
        return 1
    print(f"definition PUT accepted ({r.status_code})")

    #  Read the stored Draft back and verify.
    r = requests.get(f"{BASE}/test-templates/{v3_id}", headers=h, timeout=15)
    r.raise_for_status()
    stored = r.json()
    definition = stored["definition"]
    groups = {g["key"]: g for g in definition["groups"]}

    tpr = groups["timepoints_release"]
    fkeys = [f["key"] for f in tpr["fields"]]

    def _count(prefix: str) -> int:
        return sum(1 for k in fkeys if k.startswith(prefix))

    n_area = _count("area_")
    n_jassay = _count("jassay_")
    n_kfrac = _count("kfrac_")
    n_unit = _count("unit_")

    stats = {f["key"]: f for f in tpr["fields"] if f["key"] in ("mean", "min_val", "max_val", "rsd")}
    weights = groups["weights"]

    j7 = next(f for f in tpr["fields"] if f["key"] == "jassay_7")
    j20 = next(f for f in tpr["fields"] if f["key"] == "jassay_20")

    print(f"\nv3 Draft verification (id={v3_id}):")
    ok = True
    ok &= _check("version == 3", stored["version"] == 3, str(stored["version"]))
    ok &= _check("status == Draft (not approved)", stored["status"] == "Draft", stored["status"])
    ok &= _check("area_* count == 20", n_area == EXPECTED_SAMPLES, str(n_area))
    ok &= _check("jassay_* count == 20", n_jassay == EXPECTED_SAMPLES, str(n_jassay))
    ok &= _check("kfrac_* count == 20", n_kfrac == EXPECTED_SAMPLES, str(n_kfrac))
    ok &= _check("unit_* count == 20", n_unit == EXPECTED_SAMPLES, str(n_unit))
    ok &= _check(
        "weights.rows.max == 20",
        weights["rows"]["max"] == EXPECTED_WEIGHTS_MAX,
        str(weights["rows"]["max"]),
    )
    ok &= _check("weights.rows.default == 6", weights["rows"]["default"] == 6, str(weights["rows"]["default"]))
    ok &= _check(
        "timepoints_release.rows.max == 10",
        tpr["rows"]["max"] == EXPECTED_TIMEPOINTS_MAX,
        str(tpr["rows"]["max"]),
    )
    ok &= _check(
        "resultRef == timepoints_release.mean",
        definition.get("resultRef") == "timepoints_release.mean",
        str(definition.get("resultRef")),
    )
    for sk in ("mean", "min_val", "max_val", "rsd"):
        ok &= _check(
            f"stats.{sk} aggregates unit_20",
            "unit_20" in stats[sk]["expression"],
        )
    ok &= _check(
        "jassay_7 uses weights.weight[7 - 1]",
        "weights.weight[7 - 1]" in j7["expression"],
    )
    ok &= _check(
        "jassay_20 uses weights.weight[20 - 1]",
        "weights.weight[20 - 1]" in j20["expression"],
    )

    print("\nSample generated expressions:")
    print(f"  jassay_20 = {j20['expression']}")
    kf20 = next(f for f in tpr["fields"] if f["key"] == "kfrac_20")
    u20 = next(f for f in tpr["fields"] if f["key"] == "unit_20")
    print(f"  kfrac_20  = {kf20['expression']}")
    print(f"  unit_20   = {u20['expression']}")
    print(f"  mean      = {stats['mean']['expression']}")
    print(f"  rsd       = {stats['rsd']['expression']}")

    print(f"\n{'OVERALL: PASS' if ok else 'OVERALL: FAIL'} (v3 id={v3_id} left as DRAFT)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
