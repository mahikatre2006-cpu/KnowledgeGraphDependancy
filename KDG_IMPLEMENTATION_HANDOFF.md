# KDG Implementation Handoff Report

> **Generated:** 2026-10-11  
> **Repository:** APSIT AIML Knowledge Dependency Graph (KDG)  
> **Status:** Stage B Frozen (Approved Gate: 8–70 topics/subject, 3–20 topics/module). P0–P4 Implementation Complete.

---

## 1. Executive Summary & Verification

This handoff documents the resolution of the broken live application and unreliable model pipeline, addressing root causes identified in `MODEL_FIX_PLAN.pdf` and `PLAN.md`:

1. **Stage B Resolution & Freeze:**
   - Evaluated `DATA/review/extraction_pilot_v3_candidate.csv` against the approved revised bounds: **8–70 topics per subject**, **3–20 topics per module**.
   - Verified MVC in `ITC501` Module IV (`Model-View-Controller Framework`, quote: `Model-View-Controller framework`, p. 13) was added.
   - Verified REST API in `ITC501` was already canonically present in Module I (Row 10, quote: `REST API`, p. 13); duplicate node avoided.
   - Candidate V3 contains exactly **180 rows** across all 3 pilot courses (`ITC501`: 61, `CSC303`: 52, `2113112`: 67). 100% of rows pass quote grounding against source syllabi. Stage B is frozen.

2. **P0 — Live Parser Noise Elimination:**
   - Created `app/parser/syllabus_extractor.py` and `app/parser/pdf_parser.py`, resolving the critical `ModuleNotFoundError: No module named 'app.parser'` bug that broke FastAPI upload endpoints.
   - Ported offline noise-cleaning rules and regex filters to eliminate observed junk strings (`THIS IS A STUDENT`, `OFFICIAL UNIVERSITY`, `PREPARED FOR STUDY AND SYLLABUS`, `DEMO / REFERENCE COPY`, `PAGE 2`, and rubric/marking boilerplate) while preserving genuine technical concepts (e.g., `Object-Oriented Programming`, `Binary Search Trees`, `Linear Algebra`).
   - Added automated regression tests in `tests/test_parser.py`.

3. **P1 — Frontend / Backend Integration & Graph Inference:**
   - Traced the frontend flow: `FileUpload.jsx` calls `/pipeline/upload-and-parse` followed by `/pipeline/build-and-infer` with `add_unit_sequential_edges=False`.
   - Identified and fixed the root backend gap in `app/api/builder_router.py`: `build-and-infer` built nodes from syllabus but never called `RelationshipInferencer.infer_prerequisites`, returning 0 edges to the UI.
   - Connected `RelationshipInferencer.infer_prerequisites(graph=global_graph, auto_add_to_graph=True)` in `build-and-infer`.
   - Validated node IDs, edge endpoints, cycle prevention (`SequenceEngine.find_cycle`), and in-degree capping ($\le 3$ parents) to maintain DAG integrity without inventing artificial edges.

4. **P2 & P3 — Train–Serve Parity & Model Provenance:**
   - Fixed the train–serve parity bug in `app/services/relationship_inferencer.py`: `order_delta` was formerly computed as `abs(unit_a - unit_b)` (coarse 0–5 unit difference) while training expected topic-index difference `j - i`. It now passes `order_delta = max(1, j - i)`.
   - Created `app/ml/train_v4.py`, eliminating the undocumented artifact issue (`model_artifact_v3.joblib`). Filtered out all 836 circular heuristic-formula labels from `final_training_dataset.csv`, retaining the 335 non-heuristic rows.
   - Trained `model_artifact_v4.joblib` with subject-held-out validation. Saved artifact, metadata (`model_artifact_v4_meta.json`), and feature schema.
   - Equipped `ClassifierInferenceService` with a strict feature schema guard to prevent silent feature drift.

5. **P4 — Acceptance & Offline Doctrine (AC-0):**
   - Verified AC-0 offline doctrine via `tests/test_offline_prediction.py`: running with `$env:GEMINI_API_KEY=""` and zero network access executes syllabus parsing, node construction, local embeddings, XGBoost edge inference, and topological sort with exit code 0.

---

## 2. Changed and Created Files

| File | Change Type | Description |
|---|---|---|
| `app/parser/__init__.py` | Created | Package entrypoint exposing parser services |
| `app/parser/pdf_parser.py` | Created | PyMuPDF text extractor and whitespace/encoding normalizer |
| `app/parser/syllabus_extractor.py` | Created | Live regex parser with noise filters rejecting junk strings while preserving concepts |
| `app/models/parser/syllabus_extractor.py` | Modified | Backward-compatibility alias re-exporting from `app.parser` |
| `app/models/parser/pdf_parser.py` | Modified | Backward-compatibility alias re-exporting from `app.parser` |
| `app/api/builder_router.py` | Modified | Connected `RelationshipInferencer` to `build-and-infer` and optional `run_inference` |
| `app/services/relationship_inferencer.py` | Modified | Fixed `order_delta` to topic index gap `j - i`, added parent-count cap, endpoint validation |
| `app/services/classifier_inference_service.py` | Modified | Added default loading of `model_artifact_v4.joblib` and runtime feature schema guard |
| `app/graph/models.py` | Modified | Added `tier: str = "strong"` attribute to `DependencyEdge` |
| `app/graph/engine.py` | Modified | Added `tier` parameter to `KnowledgeGraph.add_dependency` |
| `app/ml/train_v4.py` | Created | Committed reproducible training script with subject-held-out evaluation |
| `app/ml/model_artifact_v4.joblib` | Created | Retrained XGBoost classifier trained strictly on non-heuristic pairs |
| `app/ml/model_artifact_v4_meta.json` | Created | Provenance metadata, SHA-256 hash, threshold, and feature schema for v4 |
| `tests/test_parser.py` | Modified | Added regression test `test_junk_nodes_filtering_regression` for 5 junk nodes |
| `tests/test_builder.py` | Modified | Added integration test `test_build_and_infer_end_to_end_ml_integration` |
| `tests/test_offline_prediction.py` | Created | AC-0 acceptance test verifying offline prediction with `GEMINI_API_KEY=""` |

*Note: Frontend files (`frontend/`) and `full_pipeline.py` were not modified, strictly adhering to KDG rules.*

---

## 3. Test Command Outputs

All numbers below were generated by live test executions:

### 3.1 Full Test Suite (`pytest tests/`)
```
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\Siddhesh\Documents\KnowledgeGraphDependancy
plugins: anyio-4.12.1, asyncio-1.4.0
collected 47 items

tests\test_analytics.py ....                                             [  8%]
tests\test_builder.py ....                                               [ 17%]
tests\test_graph.py ........                                             [ 34%]
tests\test_inference.py ....                                             [ 42%]
tests\test_main.py ...                                                   [ 48%]
tests\test_ml.py ....                                                    [ 57%]
tests\test_offline_prediction.py .                                       [ 59%]
tests\test_parser.py .......                                             [ 74%]
tests\test_persistence.py ...                                            [ 80%]
tests\test_recommendations.py ...                                        [ 87%]
tests\test_sequence.py ......                                            [100%]

======================= 47 passed, 4 warnings in 20.28s =======================
```

### 3.2 Parser Regression Tests (`pytest tests/test_parser.py`)
```
============================= test session starts =============================
collected 7 items
tests\test_parser.py .......                                             [100%]
============================= 7 passed in 12.96s ==============================
```
*Confirmed: 'THIS IS A STUDENT', 'OFFICIAL UNIVERSITY', 'PREPARED FOR STUDY AND SYLLABUS', 'DEMO / REFERENCE COPY', and 'PAGE 2' are 100% rejected; all legitimate technical concepts survive intact.*

### 3.3 Model v4 Training & Evaluation (`python app/ml/train_v4.py`)
```
============================================================
KDG — Prerequisite Edge Classifier v4 Training Pipeline
============================================================
Dataset Provenance: Filtered legacy dataset (final_training_dataset.csv) with all 836 heuristic-labeled rows removed
Total Rows: 335 | Positives: 89 | Negatives: 246
Train Rows: 200 (Subjects: 6)
Held-Out Test Rows: 135 (Subjects: 1)
------------------------------------------------------------
Optimal Decision Threshold: 0.4
Held-Out Test Precision:   0.7500
Held-Out Test Recall:      0.8182
Held-Out Test F1 Score:    0.7826
Held-Out Test ROC-AUC:     0.9597
Feature Importances:
  embedding_similarity     : 0.3198
  keyword_overlap          : 0.1086
  order_delta              : 0.5717

Saved model artifact to: app/ml/model_artifact_v4.joblib
Saved metadata to: app/ml/model_artifact_v4_meta.json
============================================================
```

### 3.4 AC-0 Offline Acceptance Test (`pytest tests/test_offline_prediction.py`)
```
============================= test session starts =============================
collected 1 item
tests\test_offline_prediction.py .                                       [100%]
============================= 1 passed in 19.76s ==============================
```
*Confirmed: Offline execution with GEMINI_API_KEY="" succeeds with 0 external network calls.*

---

## 4. Current Status Breakdown

| Subsystem | Status | Details |
|---|---|---|
| **Parser** | **OPERATIONAL (PASS)** | Noise rules active; junk nodes rejected; technical concepts preserved; import paths fixed. |
| **Backend Inference** | **OPERATIONAL (PASS)** | `/pipeline/build-and-infer` executes ML inference; node IDs & endpoints validated; DAG acyclicity enforced. |
| **Train–Serve Parity** | **RESOLVED (PASS)** | Serving uses linear topic-index gap `j - i` matching training; shared feature schema enforced. |
| **Model Training** | **RESOLVED (PASS)** | `train_v4.py` script committed; heuristic labels filtered; model artifact v4 saved with full metadata. |
| **Frontend Integration** | **OPERATIONAL (PASS)** | Backend endpoints match frontend contracts (`FileUpload.jsx` & `App.jsx`); real backend inference delivered. |
| **End-to-End Testing** | **PASS (47/47 tests)** | 100% test pass rate across parser, graph, inference, builder, and offline verification. |

---

## 5. Unresolved Blockers & Next Actions

1. **Phase 2 & Phase 3 Bulk Extraction & Labeling (Blocked by Design):**
   - Per the explicit instruction: *"Do not initiate bulk extraction yet."*
   - Bulk extraction across remaining 117 subjects requires ~132 Gemini API calls (Phase 2), followed by ~260 calls for two shuffled teacher labeling runs (Phase 3).
   - Once the user explicitly approves initiating bulk extraction, Phase 2 (`scripts/phase2_extraction_gate.py`) and Phase 3 (`scripts/phase3_labeling_gate.py`) can be launched to produce `training_table_v4.csv` for full curriculum training.

2. **Hand-Checked 300-Pair Gold Set:**
   - Per KDG doctrine, the AI agent never fills `human_label` or gold-set annotations.
   - When Phase 5 is triggered, `DATA/review/gold_set_300.csv` will be generated with flat-random sampling (seed 42) and `human_label` left blank for human annotators.

