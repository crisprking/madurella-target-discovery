"""audit_rules_v1 — LOCKED.

Verbatim from cell 134 (derive_m5_tier) + cell 136 (punitive aggregation +
positive control override). Bump version, do not edit. SHA-256 is recorded in
m6_h3_manifest.json.
"""
from typing import Iterable, Set


TIER_ORDER = (
    "A_established_fungal_chemistry",
    "B_fungal_validated",
    "C_novel_target_high_confidence",
    "D_low_priority",
)

POSITIVE_CONTROLS = frozenset({
    "KXX78641.1", "KXX73065.1", "KXX77301.1",
    "KXX74332.1", "KXX76007.1",
})


def safe_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if v is None:
        return False
    return str(v).strip().lower() in ("true", "t", "1", "yes", "y")


def derive_m5_tier(r) -> str:
    """Per-row tier — VERBATIM cell-134 logic.

    Order matters: A > B (3 paths) > D (audit-rejected ChEMBL) > C (default).
    """
    ev = str(r.get("m4_5_evidence", "")).lower()
    has_hum  = safe_bool(r.get("human_target_chemistry", False))
    has_bact = safe_bool(r.get("bacterial_target_chemistry", False))
    has_mism = safe_bool(r.get("target_class_mismatch", False))
    fung     = safe_bool(r.get("fungal_chemistry_present", False))
    lit_val  = safe_bool(r.get("literature_validated", False))
    low_drug = safe_bool(r.get("low_intrinsic_druggability", False))
    disq = has_hum or has_bact or has_mism

    # Tier A: strong/moderate ChEMBL evidence + fungal chemistry + no disqualifier
    if ev in ("strong", "moderate") and fung and not disq:
        return "A_established_fungal_chemistry"
    # Tier B path 1
    if ev == "literature_validated" and not disq:
        return "B_fungal_validated"
    # Tier B path 2
    if ev == "manual_annotation" and fung and not disq:
        return "B_fungal_validated"
    # Tier B path 3 (boolean literature_validated + fungal chemistry, no disq)
    if lit_val and fung and not disq:
        return "B_fungal_validated"
    # Tier D: had ChEMBL evidence but it was audit-flagged
    if ev in ("strong", "moderate", "weak") and disq:
        return "D_low_priority"
    # Low intrinsic druggability alone is also Tier D (Cell-134 rule)
    if low_drug:
        return "D_low_priority"
    # Tier C: discovery default
    return "C_novel_target_high_confidence"


def aggregate_punitive(row_tiers: Iterable[str]) -> str:
    """Per-gene aggregation — VERBATIM cell-136 'TRULY FINAL' rule.

    If ANY row of the gene is Tier D, the gene is Tier D. Otherwise take
    the best (lowest in TIER_ORDER) tier present.

    Rationale: a gene's drug-relevant chemistry being audit-rejected is the
    entire signal. Other un-flagged Pfam rows from the same multidomain
    protein are NOT independent rescue signals — they are other domains of
    the same protein.
    """
    tiers: Set[str] = set(row_tiers)
    if "D_low_priority" in tiers:
        return "D_low_priority"
    for t in TIER_ORDER:
        if t in tiers:
            return t
    return "C_novel_target_high_confidence"


def apply_positive_control_override(gene_id: str, tier: str) -> str:
    """Lift PC genes to at least Tier B as the FINAL step (cell 136)."""
    if gene_id not in POSITIVE_CONTROLS:
        return tier
    rank = {t: i for i, t in enumerate(TIER_ORDER)}
    if rank[tier] > rank["B_fungal_validated"]:
        return "B_fungal_validated"
    return tier


def assign_gene_tiers(audited_df) -> "pd.Series":
    """Full pipeline: per-row tier → punitive aggregation → PC override."""
    import pandas as pd
    df = audited_df.copy()
    df["_row_tier"] = df.apply(derive_m5_tier, axis=1)
    gene_tier = (df.groupby("mm_gene_id")["_row_tier"]
                   .apply(aggregate_punitive)
                   .reset_index()
                   .rename(columns={"_row_tier": "m5_gene_tier"}))
    gene_tier["m5_gene_tier"] = gene_tier.apply(
        lambda r: apply_positive_control_override(
            r["mm_gene_id"], r["m5_gene_tier"]),
        axis=1)
    return gene_tier.set_index("mm_gene_id")["m5_gene_tier"]
