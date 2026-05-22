# madurella-target-discovery

Audit-aware bioinformatic triage of the *Madurella mycetomatis* proteome for
novel antifungal drug-target candidates.

**10,707 annotated proteins → 1,085 essential homologs → 64 structural
candidates → 7-gene hardened shortlist**, with 14 Tier-D demotions documented
and justified.

*Madurella mycetomatis* is the leading cause of eumycetoma — a WHO neglected
tropical disease whose current standard of care is 9–12 months of itraconazole
plus surgical excision, with cure rates around 25–35% and amputation common.
No antifungal has ever been developed specifically for this organism.

This pipeline applies a seven-stage triage — orthology → essentiality → host
divergence → structural druggability → ChEMBL evidence → adversarial chemistry
audit → structural reliability cross-check — to identify defensible candidates
for the next round of experimental work.

The core methodological contribution is the **audit step (M4.5)**: standard
ChEMBL-activity-count pipelines fail in characteristic ways on under-curated
organisms, and an explicit adversarial audit is what makes the shortlist
defensible. See `docs/madurella_substack.md` for the full write-up.

## Final shortlist (7 genes)

| # | Gene | Tier | Comp | fpocket | pLDDT | M6 verdict | Role |
|---|------|------|------|---------|-------|-----------|------|
| 1 | `KXX78641.1` | A — established fungal chemistry | 19.0 | 0.001 | 73.0 | no detector pocket, biology only | Chitin synthase CHS2 — positive control, nikkomycin Z Phase II |
| 2 | `KXX77303.1` | B — fungal validated | 17.0 | 1.000 | 90.0 | fpocket only | DAO / FAD oxidase — largest pocket in dataset (1,484 Å³) |
| 3 | `KXX73065.1` | B — fungal validated | 16.0 | 0.943 | 58.9 | reliability demoted | Brr6 / nuclear envelope — PC, pLDDT-demoted (low confidence) |
| 4 | `KXX77301.1` | B — fungal validated | 17.0 | 0.001 | 76.9 | no detector pocket, biology only | IPC synthase — PC, aureobasidin A target (membrane) |
| 5 | `KXX76847.1` | B — fungal validated | 16.0 | 0.000 | 94.5 | no detector pocket, biology only | DHBP synthase — riboflavin biosynthesis, absent in humans |
| 6 | `KXX74332.1` | B — fungal validated | 9.0 | 0.011 | 82.9 | no detector pocket, biology only | EF-3 — PC, fungal-specific translation elongation factor |
| 7 | `KXX81897.1` | C — novel, high confidence | 16.0 | 0.749 | 93.2 | fpocket only | **Ipi1 / 60S biogenesis — cleanest novel signal; no prior chemistry** |

**Headline finding.** `KXX81897.1` (Ipi1, 60S ribosome biogenesis) is the
cleanest novel-target signal in the dataset — fpocket Druggability 0.749,
pLDDT 93.2 (well-folded), pocket volume 497 Å³, and zero prior chemistry.
Essential in yeast; the human ortholog (TEX10) carries a large C-terminal
extension absent in the fungal protein, which the pipeline's orthogroup
threshold did not flag — the selectivity question is structural-biology,
not orthology-distance. This is the gene the pipeline exists to find.

**Pocket-filter caveat.** Four of five M1 positive controls (CHS2, IPC
synthase, EF-3, DHBP synthase) score below the 0.5 fpocket floor — these
are membrane targets and large multidomain enzymes whose active sites
monomer AlphaFold does not present cleanly. They remain in the shortlist
via a documented positive-control override and biological precedent
(nikkomycin Z, aureobasidin A, etc.). The pipeline is honest about this:
the structural filter has a real blind spot for the very class of targets
that has historically yielded antifungals.

## Tier D — 14 audit-disqualified genes (the audit's actual catch)

Standard pipelines would have ranked these high. The audit's **punitive
aggregation** rule demotes the entire gene if any of its Pfam domains has
disqualifying ChEMBL chemistry (mammalian-only, bacterial-only, or
target-class collapse). This prevents a high composite score from masking
selectivity liabilities.

| Gene | Composite | Domain | Audit verdict |
|------|-----------|--------|---------------|
| `KXX77519.1` | **24.0** | MFE-2_hydrat-2_N | mammalian chemistry (100%); target class mismatch — *was M4 #1* |
| `KXX77518.1` | 20.0 | FAS_I_H | bacterial chemistry (100%) |
| `KXX77326.1` | 18.0 | HATPase_c | mammalian chemistry (100%) — fungal Hsp90 |
| `KXX76006.1` | 18.0 | CID | mammalian chemistry (100%) |
| `KXX79193.1` | 17.0 | SYY_C-terminal | bacterial chemistry (100%) — aminoacyl-tRNA synthetase |
| `KXX73700.1` | 16.0 | GHMP_kinases_N | mammalian chemistry (98%) |
| `KXX80486.1` | 16.0 | Nup192 | mammalian chemistry (100%) |
| `KXX77587.1` | 16.0 | Ost4 | mammalian chemistry (100%) |
| `KXX82531.1` | 8.0 | bZIP_2 | mammalian chemistry (100%); low druggability (TF-DNA binding) |
| `KXX77446.1` | 7.0 | ADH_N | mammalian chemistry (100%) |
| `KXX73807.1` | 4.0 | Mur_ligase_C | bacterial chemistry (100%) — cell wall biosynthesis |
| `KXX82559.1` | 0.0 | LRR_9 | mammalian chemistry (100%) |
| `KXX77243.1` | -0.5 | PB1 | mammalian chemistry (100%); class mismatch; low druggability |
| `KXX82884.1` | -1.0 | Guanylate_cyc | mammalian chemistry (100%) — soluble guanylate cyclase |

The headline case is `KXX77519.1` (SAT) — the original M4 #1 ranked target
at composite 24.0. Its ChEMBL chemistry had collapsed onto HDAC4 (histone
deacetylase), a remote acetyltransferase-fold neighbour. Without the audit,
the project would have shipped a serine-acetyltransferase recommendation
backed by 384 records of pure HDAC chemistry — phantom evidence for the
wrong target class.

## Pipeline stages

| Stage | Filter | Genes |
|-------|--------|-------|
| M0 | Pfam-A completeness vs *S. cerevisiae* / *A. fumigatus* | 10,707 |
| M1 | SGD-essential orthologs, no druggable human paralog | 1,085 |
| M2 | Host divergence (jackhmmer + Pfam-architecture delta) | 137 |
| M3 | AlphaFold + fpocket druggability | 64 |
| M4 | ChEMBL/BindingDB drug-evidence annotation | 64 (annotated) |
| M4.5 | Adversarial chemistry audit (5 rules, Tier A/B/C/D) | 64 (tiered) |
| M5 | Gated scoring: tier + composite >= 10 + pocket >= 0.5 + pLDDT >= 70 | 7 |
| M6 | P2Rank cross-check + per-pocket pLDDT/PAE + frozen rules | 7 hardened |

## Audit rules — frozen and hash-verified

**SHA-256:** `874c99125261162a77d4b67ca06ccce448a13f59beead6b619fc9602d5a3f934`

Twelve verification cases in `audit_rules_v1_tests.py` lock the expected
tier assignment for sentinel genes — SAT to Tier D, Hsp90 to Tier D, CHS2
to Tier A, Ipi1 to Tier C, and so on. All twelve must pass before any tier
assignment is accepted as canonical:

```bash
python scripts/hardening/audit_rules_v1_tests.py
```

The five audit rules:

1. **Target organism (mammalian)** — >=70% mammalian ChEMBL activity demotes the row.
2. **Target organism (bacterial)** — >=70% bacterial activity demotes the row.
3. **Target-class consistency** — Pfam-to-ChEMBL mapping that collapses unrelated drug-target classes (the SAT to HDAC4 case) demotes the row.
4. **Intrinsic druggability** — PPI / scaffold / TF-DNA-binding / cytoskeletal Pfam classes are flagged regardless of activity count.
5. **Manual-annotation rehabilitation** — literature-validated fungal-specific biology (DHBP synthase, DAO) is promoted above the activity-count metric.

**Punitive aggregation.** Any Tier-D Pfam domain demotes the entire gene to
Tier D. The five M1-declared positive controls have an explicit override
(with audit trail).

## What this pipeline does NOT claim

- We did not discover a drug. We identified seven genes worth wet-lab attention.
- Tier B is anchored on positive controls; only one Tier B gene (DHBP synthase) was surfaced by the pipeline as a non-PC literature-validated promotion.
- ChEMBL coverage for fungal targets is sparse; the audit rules are judgment calls, not statistics.
- One positive control (PMA1, `KXX76007.1`) was excluded from structural analysis for lack of an AlphaFold model.

## Pre-publication verification

A standalone verification script (`pre_publication_audit_verification.py`)
runs five independent checks against the locked artifacts and the public
ChEMBL API. From a fresh clone:

```bash
git clone https://github.com/crisprking/madurella-target-discovery
cd madurella-target-discovery
python pre_publication_audit_verification.py
```

Exit 0 = safe to ship. Exit 1 = a load-bearing claim failed.

## License

Code: MIT (see LICENSE) · Data: CC BY 4.0

A personal project. Mistakes are mine.
