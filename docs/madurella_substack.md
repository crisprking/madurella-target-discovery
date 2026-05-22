# Why your bioinformatics pipeline needs an adversarial step

*Audit-first target discovery for a neglected fungal pathogen — and what a single audit rule turned up.*

---

## TL;DR

I ran a target-discovery pipeline on *Madurella mycetomatis*, the fungus behind eumycetoma — a WHO neglected tropical disease (and on the WHO fungal-priority-pathogens list) whose current treatment is twice-daily itraconazole for nine to twelve months in combination with surgical excision. Cure rates can be as low as 26%; amputation is often required when treatment fails. Recurrence is common, and many patients do not complete the regimen, largely because they cannot afford it. Fosravuconazole — repurposed from onychomycosis, evaluated by DNDi in the first-ever randomised eumycetoma trial (Fahal et al., *Lancet Infect Dis* 24(11):1254–1265, Nov 2024) — was not superior to itraconazole in efficacy (50% / 65% / 75% complete cure at 12 months across the 300 mg fos, 200 mg fos, and itraconazole arms, mITT), but offered practical advantages: once-weekly dosing, no food requirement, lower drug–drug interaction burden. The chemistry pipeline against this organism is still wide open for new target classes.

The computational triage went from **10,707** annotated proteins to **1,085** essential homologs to a final shortlist of **seven genes**, including one clean novel-target signal: `KXX81897.1` — fungal **Ipi1**, a component of the Rix1 60S ribosome-biogenesis complex, well-folded by AlphaFold (pLDDT 93.2), with an fpocket Druggability score of 0.749 and no prior chemistry against this gene in ChEMBL as of the locked query date. (Humans have a homologous protein, TEX10, that the pipeline's orthogroup threshold did not flag — discussed in §6.)

The interesting result was not the shortlist. It was the **fourteen genes the pipeline initially ranked highly and the audit step caught**. The number-one target post-M4 was a serine acetyltransferase — `KXX77519.1`, composite score 24.0 — whose ChEMBL evidence turned out to be **384 records of histone deacetylase 4 chemistry**, mapped onto SAT through a remote acetyltransferase-fold similarity. Wrong target class, wrong organism, no fungal selectivity. Without an audit, that would have been the headline recommendation.

This post is about why I think every ChEMBL-driven target list needs an adversarial audit step, what five rules turned out to matter, and what falls out the bottom when you write them down.

The code, data, and audit decisions are all on GitHub: [crisprking/madurella-target-discovery](https://github.com/crisprking/madurella-target-discovery).

---

## 1. The problem with this organism in particular

Eumycetoma is endemic in the "mycetoma belt" — Sudan, Mauritania, Senegal, Mexico, India, and a tail of cases reaching into Kenya and Ethiopia — and primarily affects subsistence farmers and herders walking barefoot in contaminated soil. The fungus inoculates through a thorn-prick, lies dormant for months, then produces a slow-growing granulomatous mass that destroys soft tissue and bone. By the time most patients reach a clinic, the realistic options are a year of itraconazole, surgical debridement, or amputation.

The numbers are not abstract. A year of itraconazole costs roughly USD $2,160 [^1] — about a month's salary per month of treatment in endemic communities [^2] — and the largest prospective study (1,242 patients at the Mycetoma Research Centre, Khartoum) reported a 25.9% cure rate, 54% loss-to-follow-up, and post-surgical recurrence in a quarter to a half of cases, primarily for cost and side-effect reasons [^3].

[^1]: GHIT Fund mycetoma portfolio summary, citing DNDi access reports.
[^2]: Mycetoma Research Centre / DNDi briefing (RSTMH).
[^3]: Fahal AH, *PLoS Negl Trop Dis* 11(4):e0005509 (2017); the 1,242-patient cohort statistics are restated in Elkheir et al., *PLoS Negl Trop Dis* 14(8):e0008307 (2020).

There is no validated *M. mycetomatis* drug target in ChEMBL, no dedicated discovery program at any major pharma, and the academic groups working on the organism are small. DNDi's Phase II trial of fosravuconazole represents real progress — once-weekly dosing, no food requirement, lower drug–drug interaction burden, and a safety profile suitable for chronic use — but the trial did not show fosravuconazole to be more potent than itraconazole, and the field still lacks a target-novel candidate. The clinical chemistry stack is essentially three azoles (itraconazole, voriconazole, posaconazole) and a memory of ketoconazole.

This is exactly the situation a computational target-discovery pipeline is supposed to help with: triage a proteome down to a defensible shortlist, anchored in known biology, small enough to justify experimental follow-up. The catch is that the standard ingredients — essentiality, host divergence, structural druggability, ChEMBL evidence — were developed and tuned on well-studied organisms. Applied to a fungus nobody has mapped onto ChEMBL, they fail in characteristic ways that hide in plain sight at the top of the ranking.

## 2. The pipeline, in one screen

Seven stages, each with a single concrete filter:

| Stage | Filter | Genes |
|-------|--------|-------|
| M0 | Pfam-A completeness vs *S. cerevisiae* / *A. fumigatus* (assembly QC) | 10,707 |
| M1 | SGD-essential ortholog, no detectable human ortholog with druggable paralog | 1,085 |
| M2 | Host divergence: jackhmmer + Pfam-architecture delta | 137 |
| M3 | AlphaFold structure + fpocket Druggability | 64 |
| M4 | ChEMBL + BindingDB drug-evidence annotation | 64 |
| M4.5 | **Adversarial chemistry audit** (Tier A/B/C/D) | 64 |
| M5 | Gated scoring; Tier A/B retained on biology, Tier C gated on structure | **7** |
| M6 | Post-shortlist hardening (P2Rank, per-pocket pLDDT/PAE, SHA-256 lock) | 7 hardened |

M0 through M4 are unremarkable. The pieces are well-known: OrthoFinder for orthology, jackhmmer for sensitive remote homology, HMMER + Pfam-A for architecture, AlphaFold + fpocket for structural druggability, the ChEMBL web API for activity counts. The lift over each individual tool is small; the value is in the integration.

What makes the result defensible is **M4.5** — the audit. Without it, the ranking is the ranking your inputs produce, and the inputs are wrong in interesting ways.

## 3. The discovery that prompted the audit

The first version of the pipeline ran cleanly through M4 and produced a top result that looked perfect: `KXX77519.1`, annotated as serine acetyltransferase (SAT), composite score 24.0, **384 ChEMBL activity records**, and ChEMBL's curated annotation as a serine acetyltransferase target with *O*-acetylserine-analog chemistry. The SAT-dependent cysteine biosynthesis pathway (serine → *O*-acetyl-L-serine → cysteine) is absent in mammals — we make cysteine via transsulfuration from methionine and acquire the rest from diet — so SAT looked like a textbook fungal-selective target.

I asked the obvious follow-up: *what is the top ChEMBL target that those 384 records actually come from?*

The answer was **histone deacetylase 4** (HDAC4). Not serine acetyltransferase. Not anything to do with cysteine biosynthesis. The Pfam-to-ChEMBL mapping had collapsed the SAT acetyltransferase fold onto HDAC4 — a remote topological neighbour with no functional relationship — and 384 records of mammalian HDAC chemistry had ridden in alongside.

Three things were wrong:

1. **Wrong target class.** HDAC4 is a zinc-dependent histone deacetylase. SAT is an acetyltransferase that produces *O*-acetyl-L-serine from serine and acetyl-CoA. These do not share substrate, mechanism, or pharmacology — both happen to handle acetyl groups but via entirely different chemistries.
2. **Wrong organism.** HDAC4 is human. Every one of those 384 compounds was screened against the human enzyme.
3. **No fungal selectivity argument.** Even if you imagined a compound could somehow bridge from HDAC4 to fungal SAT, there is no reason to expect it to spare any of the other mammalian acetyltransferases. Selectivity would have to be invented from scratch with no chemical starting point.

If I had shipped the list as-is, the headline recommendation would have been a target that did not exist in the chemistry that allegedly supported it.

The thing to notice is that this is not a bug in M4. The ChEMBL API returned what it was asked. The Pfam mapping is what it is. **What was missing is an adversarial step that interrogates the chemistry before promoting it to "evidence."** Any pipeline that uses activity counts as a proxy for tractability will hit this — sometimes loudly, more often silently.

## 4. Five rules and what they caught

I wrote the audit as five rules with explicit boolean outputs, each defended in code and tested against twelve sentinel cases. The full implementation is `scripts/hardening/audit_rules_v1.py` in the repo, SHA-256-locked and unit-tested.

**Rule 1 — Target organism (mammalian).** For each Pfam domain, what fraction of ChEMBL activity records come from mammalian organism IDs? ≥70% disqualifies the row. This catches Hsp90 (HATPase_c, 100% mammalian — radicicol and geldanamycin derivatives), CID, Nup192, ADH_N, MFE-2 hydratase, GHMP kinases, Ost4, bZIP_2, LRR_9, PB1, and soluble guanylate cyclase. Eleven hits. Most have published fungal biology but no fungal-selective chemistry in ChEMBL.

**Rule 2 — Target organism (bacterial).** Same idea, opposite direction. ≥70% bacterial activity disqualifies. Catches fungal type-I FAS (`KXX77518.1`, every compound screened against *E. coli* FabB/FabF), the bacterial-style aminoacyl-tRNA synthetase (SYY_C-terminal), and the Mur ligase domain. Fungal type-I FAS is structurally distinct from the bacterial type-II system that produced the chemistry; selectivity would have to be built from scratch.

**Rule 3 — Target-class consistency.** The SAT rule. For each domain, look at the top ChEMBL hits and check whether they belong to the same EC class and functional family as the Pfam annotation. Mismatches — SAT to HDAC4 (acetyltransferase to deacetylase), PB1 to MAPK kinase (scaffold domain to catalytic kinase), PAP2 to glucose-6-phosphatase (lipid phosphatase to sugar phosphatase, distantly related histidine-acid families) — disqualify regardless of organism distribution. Three high-confidence catches plus a near-miss logged in the decision log.

**Rule 4 — Intrinsic druggability.** Some Pfam classes have well-known reasons to be hard regardless of activity count: PPI domains, structural scaffolds, TF–DNA-binding domains, cytoskeletal components. Four domains receive a composite ×0.5 penalty rather than full disqualification. This is the softest rule; in this run it changed within-tier ranking but did not move any gene from Tier C to D on its own. Its effect would matter more in datasets with more borderline scaffolds.

**Rule 5 — Manual rehabilitation.** Mirror of rule 1: some genes have real fungal-specific biology that the activity-count metric dismisses. **DHBP synthase** (`KXX76847.1`, riboflavin biosynthesis) has zero ChEMBL activities, but the pathway is absent in humans — we acquire vitamin B2 from diet — and there is a substantial literature axis on the bacterial homolog (*E. coli* RibB). **DAO** (`KXX77303.1`, D-amino acid oxidase) is the more contested case: humans have a homologous enzyme (DAAO, a flavoprotein oxidase, druggable with sodium benzoate and others), and the fungal DAO is genuinely homologous to it. OrthoFinder at the inflation parameter and sensitivity used placed the fungal DAO outside the human DAAO orthogroup — a borderline call dependent on the specific parameter choice, and the audit log flags it as the most contestable single M1 exemption in the run. The Rule 5 promotion of DAO rests on a substrate-spectrum argument (the fungal enzyme's catalytic preferences are not fully overlapping with DAAO) rather than orthology distance; a reviewer who wanted to demote DAO to Tier C and re-gate on structure could do so by editing one boolean.

On top of these five, a **positive-control override**: five M1-declared positive controls (chitin synthase, IPC synthase, Brr6, EF-3, PMA1) get a Tier B floor regardless of audit outcome. If the audit pushes one below that, the audit is suspect *for that gene*, not the target.

The single most important methodological decision was **punitive aggregation**. A multidomain protein has several Pfam annotations, and most aren't tied to ChEMBL — they're unannotated in ChEMBL for that domain. The naïve rule lets unannotated domains rescue the gene: "one Pfam row is a mammalian-chemistry liability, but eight others are unannotated, so on balance the gene is fine." This is wrong. Those unannotated rows are other functions of the same protein, not independent rescue signals.

> *The rule is: any Tier-D Pfam row demotes the entire gene to Tier D. Tier D is not "this gene is not a drug target." Tier D is "the chemistry that ChEMBL currently associates with this domain does not support a fungal-selective claim." Positive-control override is the only exception.*

When I switched from "best of tiers" to punitive aggregation, SAT (`KXX77519.1`) moved from Tier C — where it had been sitting since its SAT domain was demoted to manual-annotation and rescued by unannotated partner domains — to Tier D, where it belonged. Hsp90 made the same move. So did FAS. That single rule change rewrote about a quarter of the gene-level verdicts.

## 5. The structural filter and its blind spot

The M3 filter is AlphaFold + fpocket Druggability ≥0.5, with M5 adding a pLDDT ≥70 reliability gate.

A clarification first: fpocket's Druggability score is a pocket-detection and geometric-scoring metric — it identifies cavities and ranks them by physicochemical feature combinations correlated with successful drug-binding sites. It is not a direct readout of ligandability in the kinetic, thermodynamic, or screen-hit sense. A high score is a strong hint that a pocket is the right *shape* to bind a drug-like molecule. A low score is a hint that it isn't, with several specific failure modes the next paragraph names.

Two things to know about this filter on real fungal essentials:

**The pocket score is conservative.** The median fpocket Druggability across the 62 modeled structures is 0.013. Only eight structures clear the 0.5 floor at all. That is much lower than typical surveys of essential enzymes, and the reason is that many of the M2-essential, host-divergent hits are non-catalytic — DASH kinetochore components (Dam1, Ask1, Dad1), Mediator subunits, the Sen15 tRNA-splicing component. These are real essential genes with no discrete small-molecule cavity. The pocket filter is doing the discrimination it was designed for.

**But it has a known failure mode** for the very class of targets that has historically yielded antifungals. Four of the five M1 positive controls score *below* the 0.5 floor:

| Positive control | fpocket | Why the score doesn't reflect ligandability |
|---|---|---|
| CHS2 (chitin synthase, `KXX78641.1`) | 0.001 | Membrane-embedded glycosyltransferase; AlphaFold monomer prediction doesn't present the lumenal active site. Nikkomycin Z binds it anyway. |
| IPC synthase (`KXX77301.1`) | 0.001 | Membrane-localized lipid kinase; same monomer-prediction issue. Aureobasidin A binds it anyway. |
| EF-3 (`KXX74332.1`) | 0.011 | Large multidomain ribosome-associated factor; AF monomer doesn't expose a clean cytoplasmic pocket. Decades of EF-3 chemistry exist. |
| DHBP synthase (`KXX76847.1`) | 0.000 | Active site is a small Mg²⁺-coordinated lyase site — chemically real, geometrically tiny without the bound ion. |

These are not pipeline failures in the sense that the structural filter is wrong. They are pipeline failures in the sense that **AlphaFold monomer prediction of fungal-target classes that historically yielded inhibitors is not a reliable readout of pocket druggability for membrane-embedded or multimeric active sites.** The positive controls remain in the shortlist via the explicit positive-control override, with the structural caveat documented. The repo's `M5_SHORTLIST.md` names the blind spot directly:

> *4 of 5 positive controls would have been rejected by the structural filter alone and required the positive-control override to remain in the shortlist. The filter performs the discrimination it was designed for (novel-target candidates with tractable cavities) but it has a known failure mode for the membrane and multidomain catalytic sites where many validated antifungals act.*

The Brr6 case (`KXX73065.1`) is an even more uncomfortable one to be honest about. fpocket reports 0.943 — a beautiful, druggable-looking pocket. But the AlphaFold pLDDT for the pocket-lining residues averages 58.9 — squarely in AlphaFold's "low confidence" bin (50–70), meaning the pocket geometry should be treated as uncertain regardless of how clean the cavity looks. The pocket may be entirely real, sitting inside a small folded fragment of an otherwise disordered protein. Or fpocket may be detecting a cavity that AlphaFold has hallucinated in a low-confidence region. The structural argument should not be over-weighted. The gene remains in the shortlist as a positive control with a "pLDDT-demoted" caveat in the M6 hardened verdict — a position the M6 cross-detector cell (P2Rank vs fpocket) documents quantitatively.

**The M5 gate as actually applied.** Because the structural filter has this blind spot, M5 does not apply pocket ≥0.5 and pLDDT ≥70 uniformly. The gates are:

- **Tier A or B candidates** are retained on biology (Established fungal chemistry or fungal-validated literature axis). Their structural scores are reported as caveats, not as gates. This is why DHBP synthase (Rule 5 rehabilitation, Tier B, pocket 0.000) is in the shortlist; it is also why the four positive controls survive their sub-floor fpocket scores.
- **Tier C candidates** (novel-target, no prior chemistry) must clear all three gates: composite ≥10, fpocket ≥0.5, pLDDT ≥70. This is where Ipi1 sits, and it clears all three by margin.
- **Tier D** is excluded outright. Positive controls cannot land in Tier D — that's what the override prevents.

Stating this explicitly here because the previous version of the article presented the M5 gates as a single uniform filter and a careful reader noticed that four of the seven shortlist genes violate at least one gate. They do, and the exemption logic is by tier; it is not hidden, just under-explained. The audit log shows every per-gene gate outcome and which exemption applied.

## 6. The shortlist

After M5, seven genes:

| # | Gene | Tier | Composite | fpocket | pLDDT | Role |
|---|------|------|-----------|---------|-------|------|
| 1 | `KXX78641.1` | A | 19.0 | 0.001 | 73.0 | Chitin synthase CHS2 — positive control, nikkomycin Z Phase II |
| 2 | `KXX77303.1` | B | 17.0 | 1.00  | 90.0 | DAO / FAD oxidase — largest pocket in dataset (ceiling-hit score) |
| 3 | `KXX73065.1` | B | 16.0 | 0.943 | 58.9 | Brr6 — PC, pLDDT-demoted |
| 4 | `KXX77301.1` | B | 17.0 | 0.001 | 76.9 | IPC synthase — PC, aureobasidin A target |
| 5 | `KXX76847.1` | B | 16.0 | 0.000 | 94.5 | DHBP synthase — riboflavin biosynthesis |
| 6 | `KXX74332.1` | B |  9.0 | 0.011 | 82.9 | EF-3 — PC, fungal-specific elongation factor |
| 7 | `KXX81897.1` | C | 16.0 | 0.749 | 93.2 | **Ipi1 — 60S biogenesis (NOVEL)** |

The single most actionable result is row 7. **Ipi1** is a component of the Rix1 complex, involved in pre-60S ribosome processing in yeast; essential in *S. cerevisiae*. Humans have a homologous enzyme: **TEX10** is the recognized human ortholog of yeast Ipi1, and forms the human rixosome with PELP1 and WDR18 [^5]. The pipeline's OrthoFinder run at the sensitivity used did not place the fungal Ipi1 and human TEX10 in the same orthogroup — TEX10 carries a large C-terminal extension absent in the yeast/fungal proteins, and the shared region is only ~20% identical at the sequence level — so the orthology call was "no detected human ortholog" at the pipeline's threshold, even though the biological ortholog plainly exists. The relevant question for drug discovery is not "is there a human gene from the same family?" but "is there a region of the fungal protein where selectivity can be obtained?" The 0.749 fpocket score, pLDDT 93.2 confidence, and 497 Å³ pocket volume are independent structural facts; whether that pocket can be hit selectively against human TEX10 is the experimental question. The AlphaFold model is high-confidence and no prior chemistry is recorded against the gene in ChEMBL as of the locked query date (May 2026). It is exactly the kind of result the pipeline exists to surface — but the selectivity claim is a structural-biology question that needs the human TEX10 comparison done explicitly, not assumed from the orthology threshold.

[^5]: Finkbeiner et al. (2011); Castle et al., *Mol. Biol. Cell* 22(13):2334 (2011); recent cryo-EM structures of the human rixosome — Huang & Tong, *Nat. Commun.* 16, s41467-025-58732-3 (2025); Singh et al., *Sci. Adv.* eadw4603 (2025) — explicitly identify TEX10 as the human ortholog of yeast Ipi1, with a large C-terminal extension absent from the fungal protein.

The most underrated result is row 5. **DHBP synthase** has zero ChEMBL activities and a pocket score of 0.000. By every activity-count and structural metric, the pipeline should have ignored it. The audit's manual rehabilitation rule promoted it because riboflavin biosynthesis is absent in humans, the published literature on the bacterial homolog (RibB) translates conceptually, and the 0.000 pocket reading is a known artefact of AlphaFold monomer prediction on Mg²⁺-dependent lyases rather than a real ligandability claim. This is exactly the kind of gene that standard pipelines miss and that biology-aware audits should surface.

I want to be careful about what this list is and isn't. It is a defensible candidate set for the next round of work — biochemistry, structural validation, fragment screens. It is not a drug. It is not a wet-lab result. It is the output of a computational triage that I have tried to make honest about its own limitations, including the structural-filter blind spot named above.

**Where the rest of the 64 candidates went.** Of the 64 genes that entered M5, 7 cleared the shortlist gates, 14 were demoted to Tier D by the audit (table in §7), and the remaining 43 were Tier C candidates that failed the structural or composite thresholds without being audit-disqualified — low composite (<10), sub-floor fpocket (<0.5), low pLDDT, or some combination. They are listed in `data/locked/m5_full_ranking.csv` with the per-gate disposition; they are excluded from the shortlist but are not the audit's catch. The 14 Tier-D demotions are.

## 7. The fourteen genes the audit caught

The shortlist isn't the most interesting artifact of the pipeline. The Tier-D demotions are.

Fourteen genes had ChEMBL chemistry that the audit determined to be against the wrong organism or wrong target class. These would have appeared on a naïvely scored ranking. They are listed below for two reasons: transparency about what the pipeline excluded, and as a documented set of cases where ChEMBL-as-evidence fails in characteristic ways.

| Gene | Pre-audit composite | Audited Pfam row | Audit verdict |
|---|---|---|---|
| `KXX77519.1` | **24.0** | MFE-2_hydrat-2_N [^4] | mammalian (100%); target class mismatch (SAT-fold hit → HDAC4) — *was M4 #1* |
| `KXX77518.1` | 20.0 | FAS_I_H | bacterial (100%) |
| `KXX77326.1` | 18.0 | HATPase_c | mammalian (100%) — fungal Hsp90 |
| `KXX76006.1` | 18.0 | CID | mammalian (100%) |
| `KXX79193.1` | 17.0 | SYY_C-terminal | bacterial (100%) — aminoacyl-tRNA synthetase |
| `KXX73700.1` | 16.0 | GHMP_kinases_N | mammalian (98%) |
| `KXX80486.1` | 16.0 | Nup192 | mammalian (100%) |
| `KXX77587.1` | 16.0 | Ost4 | mammalian (100%) |
| `KXX82531.1` | 8.0  | bZIP_2 | mammalian (100%); TF–DNA-binding |
| `KXX77446.1` | 7.0  | ADH_N | mammalian (100%) |
| `KXX73807.1` | 4.0  | Mur_ligase_C | bacterial (100%) — cell-wall biosynthesis |
| `KXX82559.1` | 0.0  | LRR_9 | mammalian (100%) |
| `KXX77243.1` | −0.5 | PB1 | mammalian (100%); class mismatch; low druggability |
| `KXX82884.1` | −1.0 | Guanylate_cyc | mammalian (100%) — soluble guanylate cyclase |

[^4]: `KXX77519.1` is a multidomain protein whose gene-level annotation is serine acetyltransferase (SAT). The Pfam row that carried the disqualifying ChEMBL evidence — and that the audit fired Rule 3 on — was the MFE-2_hydrat-2_N hit. Both the gene-level SAT annotation and the audited Pfam row are recorded in `m4_5_audited.csv`; the target-class mismatch (the row's ChEMBL chemistry resolving to HDAC4 rather than to any acetyltransferase) was flagged on this row.

A few of these are subtle and worth a sentence.

**Hsp90 (`KXX77326.1`)** is a known and validated fungal target — Cowen and others have published extensively on fungal Hsp90 and its role in azole resistance. So why Tier D? Because the *chemistry* in ChEMBL is overwhelmingly mammalian — radicicol, geldanamycin, ganetespib, the STA-9090 series, all developed against human Hsp90 for oncology. Fungal-selective Hsp90 chemistry exists in literature but barely appears in ChEMBL. Promoting Hsp90 to Tier A on the basis of available ChEMBL evidence would have implied that selectivity is solved when it isn't.

**Mur ligase (`KXX73807.1`)** is similar: real fungal essentiality and cell-wall biology, but the entire ChEMBL chemistry stack is bacterial — Mur ligase inhibitors developed for decades against Gram-positives and Gram-negatives. None transfers cleanly to the fungal homolog.

**FAS (`KXX77518.1`)** is the case that bothered me most. Fungal type-I FAS is genuinely different from bacterial type-II FAS, and there is a real literature axis on fungal-selective FAS inhibitors. But the ChEMBL records that hit the FAS_I_H domain are dominated by mammalian KS chemistry (orlistat, fasnall, TVB-2640) and bacterial AcpS chemistry, none demonstrated fungal-selective. The verdict is "not actionable from current ChEMBL depth," not "not a real target." A wet-lab program with a focused fungal-selective screen could rehabilitate this gene in one experiment.

This is the methodological point. Tier D is a statement about the *evidence base*, not about the *biology*. The audit is interrogating what ChEMBL currently knows, not what is true about the protein.

## 8. What this pipeline actually proved

Three things, in descending order of confidence:

**(a) Audit-aware ChEMBL integration changes about a quarter of gene-level verdicts.** Fourteen of fifty-eight non-positive-control genes with ChEMBL activity were Tier-D-demoted by the audit. The top ranked gene before audit was a phantom (SAT → HDAC4). The headline novel finding (Ipi1) survives every audit rule and has no chemistry attached to disqualify. The audit's value is measurable in concrete reranking, not in marginal score adjustments.

**(b) The five rules are imperfect but explicit.** The single biggest source of judgment in the audit is the manual-rehabilitation rule (rule 5), which currently rehabilitates two genes (DHBP synthase, DAO) based on biology that the activity-count metric dismissed. This rule is opinionated and reviewable; the repo includes every decision the audit made and why. If you disagree with my DAO rehabilitation call, you can re-run the audit with the rule disabled and see exactly which genes move (only DAO moves; DHBP stays in via biological floor because riboflavin biosynthesis has zero chemistry in either direction).

**(c) Chitin synthase ranks first.** This is the positive-control argument working as designed. If a pipeline that ends in Tier A — strong fungal chemistry, established Phase II program (nikkomycin Z), no disqualifier — fails to put CHS2 at the top of the ranking, that is a methodology problem. It does, with all five evidence lines pointing the same direction. This does not prove the methodology is right in absolute terms, but it does establish that the pipeline isn't systematically miscalibrated against the targets we have ground truth on.

## 9. Reproducibility, quality control, and limitations

The repository at [crisprking/madurella-target-discovery](https://github.com/crisprking/madurella-target-discovery) contains the polished notebook, the locked CSVs, the M6 hardening scripts, and the unit-tested audit rules. The audit module is SHA-256-locked (hash `874c99125261162a77d4b67ca06ccce448a13f59beead6b619fc9602d5a3f934`) and `audit_rules_v1_tests.py` has twelve sentinel cases that must all pass before any tier assignment is accepted. Every audit decision the pipeline made on the 64-gene candidate set is logged in `data/locked/m4_5_audited.csv`. Every gene whose tier changed between audit revisions is in `m4_5_decision_log.csv`.

The quality-control layer that I would have skipped two months ago, and now consider non-negotiable:

- **Positive controls declared in M1, before scoring.** Five genes (CHS2, IPC synthase, EF-3, Brr6, PMA1) declared with biological rationale before any ranking was computed. The commit history shows the declaration predating the M4 ranking. If positive controls are declared after seeing the rankings, the override is circular; declared before, it is a calibration check on the audit.
- **Twelve sentinel test cases.** SAT to Tier D, Hsp90 to Tier D, CHS2 to Tier A, Ipi1 to Tier C, and nine more, each with the expected tier and the reasoning. The tests run in under a second; CI catches any regression in the audit rules immediately.
- **Source SHA-256 lock on the rule module.** If the audit rules change, the hash changes; the manifest is regenerated; the change is in the commit. This makes "I ran the audit" a verifiable claim rather than an assertion.
- **Per-pocket pLDDT, not whole-protein pLDDT.** M6's `H2_per_pocket_reliability.py` computes the average pLDDT of the residues lining each detected pocket and the maximum PAE within the pocket. Whole-protein pLDDT averages over residues that have nothing to do with the binding site. Brr6's structural caveat is visible at the per-pocket layer in a way it is not at the whole-protein layer.
- **Cross-detector pocket validation.** M6's `H1_p2rank_pocket_crosscheck.py` runs P2Rank, an ML-based pocket detector trained on real ligandable sites, against the same structures. Agreement raises confidence; disagreement is flagged. DAO clears fpocket cleanly but P2Rank disagrees — that disagreement is in the hardened verdict, not hidden.

Things to be explicit about as limitations:

- **Essentiality is inherited from yeast.** The pipeline uses *S. cerevisiae* SGD essentiality as a proxy. Fungal essentialomes are deeply conserved (1,173 of 1,250 SGD-essential yeast genes are represented in orthogroups retained in *M. mycetomatis*), but a proxy is not direct evidence. Wet-lab essentiality validation for any of the seven shortlist genes would meaningfully strengthen the case.
- **AlphaFold monomer predictions have known artefacts** on disordered regions, membrane proteins, and large complexes. M6 addresses this with per-pocket pLDDT/PAE and P2Rank cross-checking, but the underlying limitation stands. The Brr6 case is the most visible example; the membrane positive controls are the most consequential.
- **ChEMBL coverage is sparse for fungal targets.** Most "fungal chemistry present" annotations are <10 records. The audit's organism-fraction rules are robust to small numerical shifts but the absolute composite rankings are not.
- **The audit rules are judgment calls.** They were designed before looking at the rankings (the order is in the repository's commit history) and the positive controls were declared in M1 with rationale. But anyone is free to disagree with rule 5 in particular, and the repo makes that disagreement precise.
- **One positive control (PMA1, `KXX76007.1`) was excluded** from the structural analysis because the AlphaFold identifier mapping for the *M. mycetomatis* PMA1 ortholog did not resolve to a retrievable AFDB record at the locked query date. The gene remains a Tier-B candidate on biology; a manual AlphaFold submission would close the gap.
- **I am not a wet-lab chemist or a microbiologist.** This is a computational triage, not an experimental result. The pipeline exists to make the next round of work tractable, not to substitute for it.

## 10. Why this matters beyond *M. mycetomatis*

The audit step is the part I would want anyone working on under-curated organisms to take away. Every part of the standard target-discovery stack — Pfam, ChEMBL, AlphaFold, fpocket — was developed and validated on well-mapped systems. Each of them fails in specific, characterisable ways on organisms without dedicated chemistry. The failures concentrate at the top of the ranking, where they do the most damage: high composite scores from misattributed chemistry get the attention; the Tier-D-equivalent gene gets the experiments.

You cannot avoid this by switching pipelines, by adding more data sources, or by adopting a different scoring rule. What you can do is **write down five rules, test them against twelve sentinels, hash the source, and ship the audit log as a first-class artifact alongside the shortlist**. That is enough. The audit doesn't need to be clever. It needs to be honest, written down, and reviewable.

There is a broader pattern here that bioinformatics is going to have to absorb. Pipelines that used to take weeks now run in days; the limit on output is no longer compute time but the discipline to know when a result is good enough to ship and when one more filter is just procrastination. Adding variables past the decision threshold is a form of false rigor. The skill the field needs to develop is not building bigger pipelines but knowing which biological problem is worth the machinery, which dataset answers the question actually being asked, and when to stop — when the next filter would not change what we would do experimentally. Precision over ornamentation, written down so a stranger can disagree.

If you have built a pipeline like this and you have not taken the top-ranked gene apart by hand to see what its ChEMBL evidence actually consists of, my strong suggestion is to do that before you do anything else. In my case the answer was 384 records of HDAC4. The next pipeline's answer will be something different and equally specific. Both are worth catching before they become recommendations.

---

*Code: MIT. Data: CC BY 4.0. A personal project. Mistakes are mine.*

*Full repository: [github.com/crisprking/madurella-target-discovery](https://github.com/crisprking/madurella-target-discovery)*
