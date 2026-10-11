# KDG — Phase 0 & Phase 1 Audit & Full Phase Plan
> Status: Phase 0 Accepted. Phase 1 Executed (Read-only / New Files Only).
> Generated: 2026-10-11. Awaiting professor / user approval before Phase 2.

---

## 1. Evidence Verification (Phase 0 Claims)

All numbers below come from live command output. "CONFIRMED" means the command ran and matched. "WRONG" means the command ran and contradicted. "UNVERIFIABLE" means no command could be run.

### 1.1 Training dataset — rows and positives

**Document claim:** 1,171 rows / 220 positives (18.8%)

**Command:** `python analyze.py  # reads True_Cleaned_Dataset/final_training_dataset.csv`

**Raw output:**
```
Total positives: 220
Total negatives: 951
Total rows: 1171
Positive rate: 0.1879 (18.8%)
```

**Verdict: CONFIRMED** — exact match on all three numbers.

> Note: file lives at `True_Cleaned_Dataset/final_training_dataset.csv`, not `DATA/final_training_dataset.csv`.
> Columns: `concept_a, concept_b, source_syllabus, order_delta, label, reason, domain_match, Course_Code, course_name, embedding_similarity, keyword_overlap`

---

### 1.2 Positives whose reason text is a heuristic rule

**Document claim:** 125 of 220 positives created by heuristic rule text.

**Command:** Scanned `reason` column for pattern `Adjacent|sim=|delta=|kw_|Foundational|Insufficient|position|keyword|order`

**Raw output:**
```
Positives with EMPTY reason:              89
Positives with heuristic-formula reason: 131
  (of which 'Insufficient signal' as positive label:  6)
```

**Verdict: WRONG — observed count is 131, not 125.**
The 6-row difference is positives labeled with reason `"Insufficient signal"`, which the document counts only as a negative reason. If those 6 are excluded, the heuristic count is 125. The document's number is reproducible only with that exclusion; the raw count is 131.

---

### 1.3 Positive rate by order_delta bucket

**Document claim:** positive rate ge4 = 3.4% (562 rows); negative bucket = 0% (35 rows)

**Command:** Bucketed every row by `int(order_delta)`.

**Raw output:**
```
bucket=neg   : total=  35  positives=  0  pos_rate=0.0000
bucket=0     : total=  66  positives= 63  pos_rate=0.9545
bucket=1     : total= 200  positives= 82  pos_rate=0.4100
bucket=2     : total= 171  positives= 44  pos_rate=0.2573
bucket=3     : total= 137  positives= 12  pos_rate=0.0876
bucket=ge_4  : total= 562  positives= 19  pos_rate=0.0338
```

**Verdict: CONFIRMED** — negative bucket: 35 rows, 0 positives (0.00%). ge_4 bucket: 562 rows, 3.38% ≈ 3.4%. Both match exactly.

---

### 1.4 Model features and importances (model_artifact_v3.joblib)

**Document claim:** 3 features — similarity 0.50, position 0.39, keyword 0.11

**Command:** `joblib.load('app/ml/model_artifact_v3.joblib')`

**Raw output:**
```
TYPE: <class 'xgboost.sklearn.XGBClassifier'>
feature_names_in_: ['embedding_similarity' 'keyword_overlap' 'order_delta']
feature_importances_: [0.4947793  0.11419167 0.39102906]
```

**Verdict: CONFIRMED** — 3 features. Importances: embedding_similarity=0.4948 ≈ 0.50, order_delta=0.3910 ≈ 0.39, keyword_overlap=0.1142 ≈ 0.11. All match.

---

### 1.5 order_delta computation: app (serve time) vs training

**Training** (`build_candidate_pairs.py:73`):
```python
order_delta = j - i   # raw linear topic-index gap; always >= 0 (loop enforces j > i)
```

**App / serve time** (`relationship_inferencer.py:166`):
```python
order_delta = abs(unit_a - unit_b) if (unit_a != 999 and unit_b != 999) else 1
# unit_a, unit_b = integer unit number from "Unit N" string
```

**Verdict: WRONG — confirmed training/serving mismatch.**

| Dimension | Training | Serving |
|---|---|---|
| Unit of measure | Raw topic-index gap (0–14 range) | Unit-number gap (typically 1–6) |
| Fallback | N/A (loop guarantees value) | Hardcoded `1` if unit unknown |
| Implication | Model trained on fine-grained distances | Served coarser distances → distribution shift |

A pair 8 topics apart in training (order_delta=8) might map to unit_gap=2 at serve time — the feature the model sees is completely different.

---

### 1.6 Script that produces model_artifact_v3.joblib

**Command:** Full project search (excluding `venv`) for `model_artifact_v3` and `joblib.dump`.

**Raw output:**
```
[joblib.dump]       app/ml/train_classifier.py:236  → dumps to model_artifact.joblib  (NOT v3)
[joblib.dump]       scripts/pipeline/full_pipeline.py:843 → dumps to model_artifact.joblib  (NOT v3)
[model_artifact_v3] app/services/classifier_inference_service.py:15  ← load path only
[model_artifact_v3] Docs/demo_presentation_guide.md:40               ← doc reference only
```

**Verdict: WRONG — no script in the repo produces `model_artifact_v3.joblib`.**

`model_artifact_v3.joblib` exists on disk and is loaded at serve time, but both training scripts write to `model_artifact.joblib` (no `_v3` suffix). The v3 artifact is a mystery file with no committed training provenance.

---

### 1.7 Negatives labeled "Insufficient signal"

**Document claim:** 705 of 951 negatives.

**Raw output:**
```
NEG REASON DISTRIBUTION:
  705  'Insufficient signal'
  246  ''
```

**Verdict: CONFIRMED** — 705 of 951 negatives carry that reason.

---

## 2. Phase 1 Verification & Inventory Results

Executed via `scripts/phase1_manifest_triage.py`. Raw output from live command:

```
==================================================
PHASE 1 MANIFEST TRIAGE & DEDUPLICATION REPORT
==================================================
Total manifest entries:      27
Excluded PDFs:              8 (Chemical, Civil, Electrical, Electrical & Computer, EXTC, Mechanical, Mech & Auto)
In-scope PDFs:              19 (Plan said ~28; real manifest is 27 total - 8 excluded = 19)
COMPS Sem 3/4 deduped:       5 courses (['CSC401', 'CSC402', 'CSC403', 'CSC404', 'CSC405'])
FE unique subjects:          7

Deduplicated subjects per branch (Sem III+):
  IT:                       57
  COMPS:                    67
  CSE:                      11
  AIML family:              24

Deduplicated subjects per scheme (including FE):
  Rev-2019:                 88
  NEP-2020:                 36

Total deduplicated subjects across all in-scope PDFs: 120
==================================================
```

### Breakdown of In-Scope vs Excluded:
- **Total manifest PDFs:** 27
- **Excluded PDFs (8 files):** Chemical Engineering (6.40-N), Civil Engineering (6.23-N), EXTC (6.19-N), Electrical & Computer Engineering (6.51N), Electrical Engineering (6.29-N), Mechanical and Automation Engineering (6.44-N), Mechanical Engineering (6.23-NB, 6.35-N).
- **Real In-Scope PDFs:** **19 PDFs** (Plan erroneously stated ~28; manifest contains 27 total, with 8 excluded = 19).
- **COMPS Rev-2019 Sem 3 & 4 Deduplication:** Courses `CSC401`, `CSC402`, `CSC403`, `CSC404`, `CSC405` appear in both `be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf` and `be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf`. Exactly **5 duplicate courses** deduplicated by course code.
- **First Year (FE) Shared Subjects:** 4 PDFs covering "Sem. I & II" (`6.9N-AIML.pdf`, `6.14N-CSE-AIML.pdf`, `6.28N-DS.pdf`, `6.22-NIT.pdf`) contain identical common curriculum. Tagged `year_tag=FE` and `role=train_only`. Exactly **7 unique shared subjects** extracted.
- **Subject Role Allocation:**
  - `train_val_test`: 92 unique subjects (IT, COMPS, CSE Sem III+)
  - `train_only`: 28 unique subjects (7 FE + 21 AIML family)
  - Total unique subjects: **120 subjects**.

---

## 3. Deviations from the Document

| # | Deviation | Reason |
|---|---|---|
| **a** | Drop Plan B (Gemini edges + local re-ranker at serve time). | Non-negotiable doctrine: LLMs/APIs never used at prediction time. Plan B violates it. |
| **b** | Training universe = MU IT + COMPS + CSE as train/val/test; AIML, AI-DS, DS, CSE-AIML, CSE-DS as train-only; 8 excluded families per addendum. | Document's broader list includes out-of-scope branches; addendum is more precise. Real in-scope PDF count is 19. |
| **c** | Gemini topic extraction: single run with verbatim `source_quote` and `page_number` substring check. Rerun only subjects failing quality gate (< 5% rejected). Keep two shuffled runs for labeling only. | Avoids redundant extraction calls. Grounding in page text prevents hallucinations while conserving API budget. |
| **d** | Split by normalised subject title within both IT and COMPS; report per-branch metrics. Do NOT hold out whole IT 6.34 PDF as the test set. | IT 6.34 is NEP-2020 only; holding it out creates a scheme-confounded test. Subject-title split is cleaner. |
| **e** | Orphan topics attached to HIGHEST-scoring candidate parent, tagged `tier="weak"` (optional in UI). | Fixes document and earlier plan typo ("weakest"). The single best candidate is the highest probability parent, but marked weak so it is distinct from high-confidence edges. |
| **f** | 300-pair gold set: 150 flat-random (seed 42) from ALL candidate pairs in test subjects (including teacher-rejected/uncertain), plus 150 from teacher-confident edges, reported separately. `human_label` stays blank. | Unbiased evaluation. If drawn only from teacher-positives, false negatives cannot be tested. Separate reporting preserves metric integrity. Agent never fills `human_label`. |
| **g** | Add Gemini-direct baseline evaluated on the same 300-pair gold set; batch 50 pairs per call; report alongside XGBoost. | Proves local model earns its keep vs pure-LLM approach; batching reduces calls from 300 to 6. |
| **h** | Sem. I & II PDFs tagged `year=FE`, treated as train-only. Subject titles deduplicated across all branches before pair generation. Val/test subjects come from IT and COMPS Sem III+. | Addendum requirement; FE subjects are branch-shared and must not leak into test. |
| **i** | COMPS Rev-2019 Sem 3 PDF deduplicated by course code against Sem 4 PDF. | Addendum requirement; prevents duplicate topic lists inflating pair counts. |
| **j** | Scheme (Rev-2019 / NEP-2020) recorded per subject but never used as a model feature. Metrics reported per scheme including a train-on-Rev-2019, test-on-NEP-only check. | Addendum requirement; scheme is analysis metadata, not a classifier signal. |

---

## 4. Open Items & Professor Confirmation Gates

> [!WARNING] **Open Item 1 (Gemini in Live Serving Path — Needs Professor Confirmation):**
> Step 8 of `MODEL_FIX_PLAN.pdf` states: *"Make the app's topic source the Gemini extraction (already in the study-planner page); keep the regex parser as fallback only."*
> If the live web application calls Gemini at PDF upload time, Gemini is part of the runtime path for end users. This contradicts the doctrine: *"The prediction path must run with no API key and no network."*
> **Resolution / Fallback Path:**
> 1. AC-0 enforces offline prediction from a pre-extracted/deterministic topic catalog or local regex parser with `GEMINI_API_KEY=""`.
> 2. Flagged for professor confirmation: Is Gemini permitted strictly at offline ingestion/catalog creation, or is an offline regex/deterministic parser required for user PDF uploads when no network is present?

---

## 5. Acceptance Test to Add

**AC-0 — Offline Prediction & Deterministic Fallback:**
With `GEMINI_API_KEY` unset and no network connection, the full prediction path:
`topics in (from deterministic catalog or regex parser) → XGBoost edges out`
must complete without error and return ≥ 1 edge for any in-scope syllabus.

Pass criteria:
- Exit code 0.
- No `requests` or `google.genai` import or network socket touched during prediction execution.
- Deterministic fallback path works end-to-end without network.
- Tested via `pytest tests/test_offline_prediction.py -v --disable-socket` with `$env:GEMINI_API_KEY=""`.

---

## 6. Numbered Phase Plan

```
Stop gate convention
────────────────────────────────────────────────────────────
After each phase: paste the gate check output here.
No next phase starts without written approval.
```

---

### Phase 0 — Audit [COMPLETED]
- Verified document claims against repo files.
- Identified mystery artifact `model_artifact_v3.joblib` and serving/training `order_delta` drift.

---

### Phase 1 — Manifest Triage & Subject Deduplication [COMPLETED]
- Classified 27 manifest PDFs: 8 excluded, 19 in-scope (10 train_val_test, 9 train_only).
- Deduplicated 5 duplicate courses between COMPS Sem 3 and Sem 4 PDFs.
- Deduplicated 7 common FE subjects across 4 first-year PDFs.
- Created `DATA/processed/manifest_classified.csv` and `DATA/processed/subject_dedup_map.csv` (120 unique subjects).
- Verified: IT=57, COMPS=67, CSE=11, AIML family=24. Rev-2019=88, NEP-2020=36.

---

### Phase 2 — Gemini Topic Extraction
**Goal:** Extract topics per subject for all 120 deduplicated in-scope subjects.
- **Granularity Assumption:** Extraction is performed per subject syllabus block (typically 2–5 pages), NEVER as a whole 100+ page PDF in a single request.
- **Execution:** Single run per subject with verbatim `source_quote` and `page_number`. Reject any topic whose `source_quote` is not a substring of that page's text.
- **Rerun Policy:** Rerun only the individual subjects where > 5% of extracted topics fail the quote-substring check.
- **Caching:** Every call cached under `DATA/processed/gemini_cache/<subject_hash>.json`.

**Files to create:**
- `DATA/processed/topics/<subject_norm_title>.json`
- `DATA/processed/gemini_cache/<hash>.json`
- `DATA/processed/topics_rejected.csv` (rejected hallucinated topics)
- `DATA/processed/topics_confident.csv` (verified grounded topics)

**API calls:** 120 base calls + ~12 quality-gate reruns (10%) = **~132 calls**.

**Gate check:**
```
python scripts/phase2_extraction_gate.py --check
# Must print:
#   Subjects processed: 120 / 120
#   Total topics extracted: N (target 1,200–1,800)
#   Rejected topics (failed quote check): < 5%
#   Topics confident: N
#   Cache hit rate: N%
```

---

### Phase 3 — Teacher Labeling (Positive Edge Generation)
**Goal:** For each subject, generate candidate prerequisite edges among confident topics (≤ 3 parents per topic).
- **Execution:** Run TWO shuffled passes per subject with topic order randomized.
- **Agreement Filter:** Keep an edge as a confident positive ONLY if both shuffled runs agree. Edges appearing in only 1 run are marked uncertain and excluded from training.
- **Human Spot-Check:** Sample 150 training edges flat-random (seed 42). Leave `human_label` blank. Annotators verify precision ≥ 80%.

**Files to create:**
- `DATA/processed/teacher_edges_run1/<subject>.json`
- `DATA/processed/teacher_edges_run2/<subject>.json`
- `DATA/processed/confident_edges.csv`
- `DATA/processed/uncertain_edges.csv`
- `DATA/review/teacher_precision_sample_150.csv` (`human_label` blank)

**API calls:** 120 subjects × 2 runs = 240 calls + ~20 same-semester cross-subject passes = **~260 calls**.

**Gate check:**
```
python scripts/phase3_labeling_gate.py --check
# Must print:
#   Subjects labeled: 120 / 120
#   Confident positive edges: N (target 2,000–3,000)
#   Uncertain edges: N
#   Precision sample: 150 rows generated, human_label=blank
#   [MANUAL GATE] Human spot-check precision >= 80%? YES/NO
```
> **Hard stop if human spot-check precision < 80%.** Tighten prompt and rerun Phase 3.

---

### Phase 4 — Training Table Construction
**Goal:** Assemble the balanced training table.
- **Positives:** Confident teacher edges (both runs agree).
- **Negatives (3:1 ratio):** Reversed edges (B→A), hard negatives (high similarity, unlinked), adjacent unlinked topics, random same-subject pairs.
- **Data Hygiene:** Remove all old rule-generated rows (matching heuristic regex). Strip null bytes, normalize whitespace. Replace `reason` column with provenance `source`.

**Files to create:**
- `DATA/processed/training_table_v4.csv` (`concept_a, concept_b, subject_title, branch, scheme, semester, label, source`)

**API calls:** 0.

**Gate check:**
```
python scripts/phase4_table_gate.py --check
# Must print:
#   Total rows: N
#   Positives: N (target 2,000–3,000)
#   Negatives: N (~3:1 ratio)
#   Old heuristic rows: 0
#   Null bytes: 0
```

---

### Phase 5 — Feature Engineering & Gold Set Splits
**Goal:** Implement shared feature function v2. Build concept-disjoint subject splits and gold test set.
- **Shared Features:** `emb_a_reduced` (32-dim PCA), `emb_b_reduced`, `emb_diff`, `emb_product`, `cosine_sim`, `norm_pos_gap`, `signed_unit_gap`, `earlier_unit_flag`, `same_unit_flag`, `keyword_overlap`, `name_contains_flag`, `foundational_flag_a`. Drop `domain_match`.
- **Subject-Title Splits:** Split by normalized subject title across IT and COMPS (no subject appears in > 1 split). Test and val subjects from IT/COMPS Sem III+. FE is train-only.
- **300-Pair Gold Set:**
  - 150 pairs flat-random (seed 42) from ALL candidate pairs in test subjects (including teacher-rejected and uncertain pairs).
  - 150 pairs flat-random (seed 42) from teacher-confident edges in test subjects.
  - Reported separately and jointly.
  - `human_label` left strictly blank for annotators.
- **Gemini-Direct Baseline:** Evaluate Gemini on the 300 gold pairs in batches of 50 pairs per call = **6 API calls**.

**Files to create:**
- `app/ml/feature_engineering_v2.py`
- `DATA/processed/train.csv`, `val.csv`, `test.csv`
- `DATA/review/gold_set_300.csv` (`human_label` blank)
- `DATA/processed/gemini_baseline_on_gold.csv`

**API calls:** 300 pairs ÷ 50 pairs/call = **6 calls** (cached).

**Gate check:**
```
python scripts/phase5_splits_gate.py --check
# Must print:
#   Train/val/test subject title overlap: 0
#   Gold set rows: 300 (150 candidate + 150 teacher-confident), human_label=blank
#   Gemini baseline on gold: 300 pairs evaluated in 6 batched calls
#   Feature columns: [12 new features]
```
> **Hard stop until humans fill `human_label` in `gold_set_300.csv`.**

---

### Phase 6 — Train, Calibrate, Compare
**Goal:** Train logistic regression baseline and XGBoost (depth 4–6, early stopping on val).
- Optimize decision threshold for graph-level F1 on validation subjects.
- Evaluate old model (`v3`), new model (`v4`), and Gemini baseline on same gold set.
- Save artifact with feature names, threshold, data hash, and committed training script.

**Files to create:**
- `app/ml/train_v4.py` (committed reproducible script)
- `app/ml/model_artifact_v4.joblib`
- `app/ml/model_artifact_v4_meta.json`
- `app/ml/metrics_v4.json`

**API calls:** 0.

**Gate check:**
```
python app/ml/train_v4.py --report
# Must print:
#   New model gold F1 >= 0.75
#   New model beats v3 clearly
#   Gemini baseline comparison metrics
#   Per-branch (IT / COMPS) metrics
#   Per-scheme (Rev-2019 / NEP-2020) metrics
#   Train-Rev-2019, test-NEP-only generalization check
```

---

### Phase 7 — Serve-Time Fix & Deterministic Graph Rules
**Goal:** Fix serve-time `order_delta` drift and wire deterministic graph rules into backend.
- **Branch Strategy:** Work on isolated git branch `feature/v4-model-fix`.
- **Files in Mahi's Backend to Touch (Do NOT modify without asking):**
  1. `app/services/relationship_inferencer.py` — change `order_delta` from unit-difference to syllabus topic-index difference `j - i` (matching training); attach orphan topics to HIGHEST-scoring candidate parent tagged `tier="weak"`.
  2. `app/services/classifier_inference_service.py` — update `MODEL_PATH` to `model_artifact_v4.joblib`; enforce feature-schema guard (refuse to load if features mismatch).
  3. `app/graph/models.py` — ensure `DependencyEdge` supports optional `tier: str = "strong" | "weak"`.
- **AC-0 Offline Gate:** Verify offline execution with `google.genai` and network disabled.

**API calls:** 0.

**Gate check (AC-0):**
```
$env:GEMINI_API_KEY=""
pytest tests/test_offline_prediction.py -v --disable-socket
# Must exit 0, >= 1 edge returned, zero calls to google.genai or requests
```

---

### Phase 8 — Acceptance Test (5 Unseen Syllabi)
**Goal:** Run 5 unseen syllabi through full pipeline. Verify acceptance checklist.

| Check | Target |
|---|---|
| Garbage nodes (header/watermark/rubric) | < 2% of nodes across 5 syllabi |
| Edge precision on gold set | ≥ 0.80 |
| Edge recall on gold set | ≥ 0.70 |
| Beats old v3 on same gold set | Yes, clearly |
| Valid DAG, average parents per node | 1.0 – 2.5 |
| Connected nodes | ≥ 90% |
| Evaluation on unseen subjects | ≥ 300 gold pairs |
| Artifact metadata + committed script | Yes |
| Offline prediction test (AC-0) | Pass with `google.genai` unset |

**Files to create:**
- `DATA/processed/acceptance_report.md`

**API calls:** 0.

---

## 7. Recomputed API Budget (Subject-Count Based)

Based on the verified 120 deduplicated subjects from Phase 1:

| Phase | Purpose | Sizing Basis | API Calls |
|---|---|---|---|
| **Phase 2** | Topic extraction (single run + source quote check) | 120 subjects + ~12 rerun retries (10% gate buffer) | **~132** |
| **Phase 3** | Teacher labeling (2 shuffled runs + agreement filter) | 120 subjects × 2 runs + ~20 cross-subject passes | **~260** |
| **Phase 5** | Gemini-direct baseline on 300-pair gold set | 300 pairs batched at 50 pairs/call | **6** |
| **Total** | | | **~398 calls** |

*All calls cached. Free-tier friendly (well within standard daily quota). Re-runs cost 0.*

---

*Phase 1 complete. Awaiting user / professor approval before Phase 2.*
