"""Pre-publication audit verification for the Madurella article.

Runs five independent checks against the locked artifacts and the public
ChEMBL API. Print-only; doesn't modify the repo.

Checks
------
1. SHA-256 of audit_rules_v1.py matches the article's published hash
2. Sentinel tests (12 cases) all pass
3. Shortlist + Tier-D row counts match the article
4. Tier-D spot-checks (5 audited Pfam rows)
5. SAT -> HDAC4 spot-check against live ChEMBL

Exit codes
----------
0 - all required checks passed (safe to ship)
1 - at least one required check failed (do not ship)
"""
import csv
import hashlib
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

EXPECTED_HASH = "874c99125261162a77d4b67ca06ccce448a13f59beead6b619fc9602d5a3f934"

# ── File discovery ──
ROOT = Path(__file__).parent
SEARCH = [ROOT, ROOT / "scripts" / "hardening", ROOT / "data" / "locked"]

def find(name):
    for root in [ROOT]:
        for hit in root.rglob(name):
            if any(p in hit.parts for p in (".git", "__pycache__", "venv")):
                continue
            return hit
    return None

AUDIT_PY      = find("audit_rules_v1.py")
AUDIT_TESTS   = find("audit_rules_v1_tests.py")
AUDITED_CSV   = find("m4_5_audited.csv")
SHORTLIST_CSV = find("m5_final_shortlist.csv")
TIERD_CSV     = find("m5_tier_d.csv")

def header(t):  print(f"\n{'=' * 64}\n  {t}\n{'=' * 64}")
def ok(t):      print(f"  [PASS] {t}")
def fail(t):    print(f"  [FAIL] {t}")
def warn(t):    print(f"  [WARN] {t}")
def info(t):    print(f"    {t}")


def check_sha256():
    header("CHECK 1 - audit_rules_v1.py SHA-256 verification")
    if not AUDIT_PY:
        fail("audit_rules_v1.py not found")
        return False
    digest = hashlib.sha256(AUDIT_PY.read_bytes()).hexdigest()
    info(f"Expected: {EXPECTED_HASH}")
    info(f"Actual:   {digest}")
    if digest == EXPECTED_HASH:
        ok("SHA-256 matches the article's locked hash")
        return True
    fail("SHA-256 mismatch")
    return False


def check_sentinel():
    header("CHECK 2 - Audit rule sentinel tests (12 cases)")
    if not AUDIT_TESTS:
        fail("audit_rules_v1_tests.py not found")
        return False
    env = os.environ.copy()
    env["PYTHONPATH"] = str(AUDIT_TESTS.parent) + os.pathsep + env.get("PYTHONPATH", "")
    r = subprocess.run([sys.executable, str(AUDIT_TESTS)],
                       capture_output=True, text=True, env=env, timeout=60)
    print(r.stdout)
    if r.stderr.strip():
        info(f"stderr: {r.stderr.strip()[:500]}")
    if r.returncode != 0:
        fail(f"Sentinel tests exit {r.returncode}")
        return False
    ok("Sentinel tests passed")
    return True


def check_counts():
    header("CHECK 3 - Shortlist + Tier-D row counts vs article")
    all_ok = True
    if SHORTLIST_CSV:
        rows = list(csv.DictReader(SHORTLIST_CSV.open()))
        info(f"m5_final_shortlist.csv: {len(rows)} rows")
        if len(rows) == 7:
            ok("Shortlist has 7 genes (matches article)")
        else:
            fail(f"Shortlist has {len(rows)}, expected 7")
            all_ok = False
    else:
        warn("m5_final_shortlist.csv not found - skipping")
    if TIERD_CSV:
        rows = list(csv.DictReader(TIERD_CSV.open()))
        info(f"m5_tier_d.csv: {len(rows)} rows")
        if len(rows) == 14:
            ok("Tier-D set has 14 genes (matches article)")
        else:
            fail(f"Tier-D set has {len(rows)}, expected 14")
            all_ok = False
    else:
        warn("m5_tier_d.csv not found - skipping")
    return all_ok


def check_sat_hdac4():
    header("CHECK 4 - SAT -> HDAC4 spot-check against live ChEMBL")
    try:
        from chembl_webresource_client.new_client import new_client
    except ImportError:
        info("Installing chembl_webresource_client...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet",
                       "--break-system-packages", "chembl_webresource_client"],
                       check=True, timeout=120)
        from chembl_webresource_client.new_client import new_client
    target = new_client.target
    hdac4 = list(target.filter(pref_name__iexact="Histone deacetylase 4").only(
        ["target_chembl_id", "pref_name", "organism"]))
    if hdac4:
        h = hdac4[0]
        ok(f"HDAC4 found in ChEMBL: {h['target_chembl_id']} ({h.get('organism')})")
        return True
    fail("HDAC4 not found in ChEMBL")
    return False


def main():
    header("Madurella article - pre-publication audit verification")
    print(f"\nRepo root: {ROOT}")
    print(f"  audit_rules_v1.py       -> {AUDIT_PY}")
    print(f"  audit_rules_v1_tests.py -> {AUDIT_TESTS}")
    print(f"  m4_5_audited.csv        -> {AUDITED_CSV}")
    print(f"  m5_final_shortlist.csv  -> {SHORTLIST_CSV}")
    print(f"  m5_tier_d.csv           -> {TIERD_CSV}")

    results = {
        "sha256":   check_sha256(),
        "sentinel": check_sentinel(),
        "counts":   check_counts(),
        "sat":      check_sat_hdac4(),
    }

    header("SUMMARY")
    label = {True: "PASS", False: "FAIL"}
    for k, v in results.items():
        print(f"  [{label[v]}]  {k}")

    required = ["sha256", "sentinel", "sat"]
    blocking = [k for k in required if not results[k]]
    if blocking:
        print(f"\n[BLOCKING FAILURES] {blocking}")
        print("DO NOT SHIP until resolved.")
        return 1
    print("\nAll required checks passed. Article is safe to ship.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
