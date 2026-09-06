# Dataset Noise Audit, Corpus Refresh & Retraining Plan

## Active Invariants (Enforced Throughout Execution)

1. **NEVER OVERWRITE ORIGINALS:** Under no circumstances will `Cleaned_Files/labeling_dataset.csv` or `app/ml/model_artifact.joblib` be modified, overwritten, or deleted. They serve as historical baseline fallbacks.
2. **DIRECTORY CONSISTENCY:** Historical training data and evaluations live in `Cleaned_Files/`. Newly ingested candidates live in `data/`. Cleaned outputs will be written to `Cleaned_Files/labeling_dataset_cleaned.csv` and mirrored to `data/labeling_dataset_cleaned.csv`.
3. **STRICT PHASE GATING:** Never advance past any phase boundary without explicit user instruction. Every phase ends with a mandatory hard stop and the required phase status line.

---

## Plan Breakdown

### Phase 0: New Candidate Corpus Regeneration (24 PDFs) — [COMPLETED]

- **Action:** Re-ran `python scripts/ingest_new_pdfs.py` using the updated, clean extractor in `scripts/full_pipeline.py` (with author/publisher filters, citation detection, mid-sentence pruning, and skipping lab/mini-project subjects).
- **Results:**
  - `data/new_candidate_pairs.csv`: 3,115 rows (clean; dropped from 14,962 contaminated rows; ~79% noise reduction)
  - `data/new_cross_domain_candidates.csv`: 2,505 rows (clean; dropped from 8,667 contaminated rows)
  - `data/review_sample.csv`: 120 stratified rows (60 it_training + 60 diversity_training), empty `your_label` column.
  - All label columns verified empty.

---

### Phase A: Historical Dataset Contamination Audit (No Modifications) — [COMPLETED]

- **Action:** Executed `scripts/audit_dataset.py` across all 3,510 rows in `Cleaned_Files/labeling_dataset.csv` using dual structural regex and semantic embedding engines.
- **Purification Findings:**
  - Total rows scanned: 3,510
  - Total rows flagged: **3,310 (94.30%)**
  - Primary reason breakdown:
    - `length_bound` (> 7 words / < 4 chars / starts lowercase): 1,962 (59.3%)
    - `truncated_fragment` (dangling words / unclosed parens / truncated tokens): 389 (11.8%)
    - `lab_or_project_course` (Mini-Project, Lab, Workshop, Capstone): 295 (8.9%)
    - `admin_rubric_noise` (exam schemes, QP note, marks, contact hours): 211 (6.4%)
    - `person_name` (author / researcher names): 203 (6.1%)
    - `publisher_citation` (textbooks, publishers, editions): 126 (3.8%)
    - `subject_mismatch` (semantic embedding divergence from course): 48 (1.5%)
    - `generic_lone_term` (overly broad single terms like 'real-time'): 42 (1.3%)
    - `tool_fragment` (hardware/tool lab prompts e.g. Raspberry Pi): 34 (1.0%)
- **Artifacts Generated:** Saved 3,310 flagged rows to `data/label_audit_flagged.csv` and `Cleaned_Files/label_audit_flagged.csv`.
- **Exit Gate:** Complete.

---

### Phase B: Human Review & Mandatory Hard Stop — [COMPLETED]

- **Action:** Evaluated flagged categories, addressed user feedback regarding residual noise in `Cleaned_Files`, and refined filter boundaries to purge all non-conceptual content while protecting authentic mathematical and computer science concepts.
- **Exit Gate:** Complete.

---

### Phase C: Cleaned Dataset Generation — [COMPLETED]

- **Action:** Executed `scripts/clean_dataset.py` to produce a completely purified, noise-free historical dataset.
- **Results:**
  - Original rows: 3,510
  - Purged rows: 3,310
  - Cleaned rows: **200 pristine conceptual topic pairs**
  - Label balance: **106 Positive (53.0%) / 94 Negative (47.0%)**
  - Target files created: `Cleaned_Files/labeling_dataset_cleaned.csv` and `data/labeling_dataset_cleaned.csv`.
  - Companion cleaned files created: `Cleaned_Files/candidate_pairs_cleaned.csv` and `Cleaned_Files/label_suggestions_cleaned.csv` (429 clean rows each).
- **Verification:** Original `Cleaned_Files/labeling_dataset.csv` verified 100% byte-identical and unmodified.
- **Exit Gate:** Complete.

---

### Phase D: Concept-Disjoint Split Verification

- **Action:** Write and run `scripts/verify_splits.py` to partition `Cleaned_Files/labeling_dataset_cleaned.csv` (70% train, 10% val, 20% test).
- **Verification:** Enforce strict disjoint condition:
  $$Concepts(Train) \cap Concepts(Test) = \emptyset \quad \text{and} \quad Concepts(Train) \cap Concepts(Val) = \emptyset$$
  Report any concept leakage or confirm zero overlap.
- **Exit Gate:** Output:
  `PHASE D COMPLETE — Concept-disjoint split verified on cleaned dataset. Awaiting go-ahead for next phase.`
  and STOP.

---

### Phase E: Model Retraining (V2) & Benchmark Comparison

- **Action:** Train XGBoost classifier on `Cleaned_Files/labeling_dataset_cleaned.csv`. Save artifact to `app/ml/model_artifact_v2.joblib` (leaving `app/ml/model_artifact.joblib` untouched).
- **Evaluation:**
  1. Evaluate on in-domain held-out test split.
  2. Evaluate on held-out `Cleaned_Files/cross_domain_test.csv` (250 rows).
- **Verification:** Produce side-by-side metrics table comparing V1 (original) vs V2 (cleaned):
  - Accuracy, Precision, Recall, F1-score, ROC-AUC, and Cross-Domain Recall.
- **Exit Gate:** Output:
  `PHASE E COMPLETE — V2 model trained and benchmarked against original model. Awaiting go-ahead for next phase.`
  and STOP.

---

## Done When

- [x] Fresh candidate corpus regenerated from 24 PDFs without noise or lab guidelines (Phase 0).
- [x] Historical dataset audited via both regex and semantic alignment engines (Phase A).
- [x] User explicitly approves purge list during Phase B hard stop (Phase B).
- [x] Cleaned dataset generated without modifying original files (Phase C).
- [ ] Concept-disjoint split verified ($Train \cap Test = \emptyset$) (Phase D).
- [ ] Model V2 trained and benchmarked side-by-side with V1 (Phase E).
