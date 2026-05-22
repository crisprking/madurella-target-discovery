"""Unit tests for audit_rules_v1.py. Must pass before locking."""
import sys
import pandas as pd
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from audit_rules_v1 import assign_gene_tiers

# Resolve m4_5_audited.csv: try data/locked/ (repo layout) and m4/ (notebook layout)
CANDIDATES = [
    HERE.parent.parent / "data" / "locked" / "m4_5_audited.csv",
    Path("/kaggle/working/m4/m4_5_audited.csv"),
    HERE.parent / "m4" / "m4_5_audited.csv",
    HERE / "m4_5_audited.csv",
]
audited_path = next((p for p in CANDIDATES if p.exists()), None)
if audited_path is None:
    print("ERROR: m4_5_audited.csv not found in any of:")
    for p in CANDIDATES:
        print(f"   {p}")
    sys.exit(2)

EXPECTED = {
    "KXX77519.1": "D_low_priority",                  # SAT -> HDAC4 (was M4 #1)
    "KXX77326.1": "D_low_priority",                  # Hsp90, mammalian
    "KXX77518.1": "D_low_priority",                  # FAS, bacterial
    "KXX82884.1": "D_low_priority",                  # sGC, mammalian
    "KXX77243.1": "D_low_priority",                  # PB1, mammalian + class mismatch
    "KXX78641.1": "A_established_fungal_chemistry",  # CHS2 PC
    "KXX73065.1": "B_fungal_validated",              # Brr6 PC
    "KXX77301.1": "B_fungal_validated",              # IPC synthase PC
    "KXX74332.1": "B_fungal_validated",              # EF-3 PC
    "KXX81897.1": "C_novel_target_high_confidence",  # Ipi1 (headline novel)
    "KXX76847.1": "B_fungal_validated",              # DHBP synthase (Rule 5)
    "KXX77303.1": "B_fungal_validated",              # DAO (Rule 5)
}

audited = pd.read_csv(audited_path)
actual = assign_gene_tiers(audited)

failures = []
for g, exp in EXPECTED.items():
    got = actual.get(g, "(missing)")
    ok = (got == exp)
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {g:<12} expected={exp:<35} got={got}")
    if not ok:
        failures.append((g, exp, got))

if failures:
    print(f"\n{len(failures)} test(s) FAILED")
    sys.exit(1)
print(f"\nAll {len(EXPECTED)} verification cases PASS")
