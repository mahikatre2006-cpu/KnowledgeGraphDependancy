# KDG — Repo Retrofit Plan (mahikatre2006-cpu/KnowledgeGraphDependancy)

**Basis:** direct inspection of the repo (fetched and read file-by-file, not inferred from the roadmap doc). Facts below are verified, not assumed — grep run across the full codebase confirms zero occurrences of `fit(`, `train_test_split`, `classifier`, `joblib`, `pickle.dump`, or `networkx`.

**Rule for whoever/whatever executes this:** this is a retrofit, not a rebuild. Every phase below states exactly which files to CREATE, which to MODIFY (and which specific function — not the whole file), and which to LEAVE ALONE. Do not touch a file not named in a phase. Do not restructure working modules "while you're in there."

---

## 0. Verified Current State

| Layer | File(s) | Status |
|---|---|---|
| Graph engine | `app/graph/engine.py`, `app/graph/models.py` | Working, tested. Custom adjacency-list DAG, no networkx. **Keep as-is.** |
| Sequencing | `app/services/sequence_engine.py` | Topological sort + cycle detection, tested. **Keep as-is.** |
| Analytics | `app/services/analytics_engine.py` | BFS ancestor/descendant traversal, reachability-based bottleneck ranking, tested. **Keep as-is.** |
| Parsing | `app/parser/pdf_parser.py`, `app/parser/syllabus_extractor.py` | PyMuPDF-based, tested. **Keep as-is.** |
| "Prerequisite prediction" | `app/services/relationship_inferencer.py` | **Not a trained model.** Hardcoded weighted formula (lines computing `confidence` — see Phase R4). This is the core gap. |
| Progress tracking | `app/db/postgres_models.py::UserProgress`, `app/api/persistence_router.py::save_user_progress` | Already exists, already has the right shape (`status`: known/in_progress/blocked). **Mostly done — extend, don't rebuild.** |
| Storage | `app/db/neo4j_driver.py`, `postgres_models.py`, `supabase_client.py` | Three backends in parallel. Neo4j is write-only, gracefully no-ops if unconfigured. |
| Frontend | `frontend/src/` on `@xyflow/react` | Correctly aligned with plan. Not part of this retrofit. |
| Dependencies | `requirements.txt` | Has unused `scikit-learn`. Missing `xgboost`, `joblib`. |

---

## Phase R1 — Dataset (blocks R2–R6, do not skip ahead)

**Create:** `data/labeling_dataset.csv` (not code — this is the human-labeled CSV from the AI-assisted, human-verified labeling workflow already agreed on). Schema: `concept_a, concept_b, embedding_similarity, order_delta, domain_match, keyword_overlap, label`.

**Create:** `data/cross_domain_test.csv` — 200–300 rows from non-IT departments. Never enters training.

**GATE — do not proceed to R2 until:** user confirms the labeled CSV exists, ≥3000 rows, no cycles, roughly balanced classes.

---

## Phase R2 — Shared Feature Module

**Create:** `app/ml/__init__.py`, `app/ml/feature_engineering.py`

```
def compute_features(concept_a, concept_b, order_delta, domain_a, domain_b) -> dict
```

**Reuse, do not duplicate:** import embedding logic from the already-existing `app/services/embedding_service.py::LocalEmbeddingService` for the `embedding_similarity` value — that service already wraps `all-MiniLM-L6-v2`, exactly what's needed. Writing a second embedding call here is the exact train/inference-drift bug to avoid.

**GATE:** show `feature_engineering.py`, confirm it's a pure function (no file I/O, no globals) and that it imports `LocalEmbeddingService` rather than reimplementing it.

---

## Phase R3 — Training Script

**Modify:** `requirements.txt` — add `xgboost>=2.0.0` and `joblib>=1.3.0`.

**Create:** `app/ml/train_classifier.py` — loads `data/labeling_dataset.csv`, splits 70/15/15 **by concept, not row**, trains `LogisticRegression` baseline then `XGBClassifier`, 5-fold CV, prints/saves accuracy/precision/recall/F1/ROC-AUC/confusion matrix to `app/ml/metrics_report.json`, saves the frozen model to `app/ml/model_artifact.joblib`.

**Create:** `app/ml/evaluate_cross_domain.py` — loads `data/cross_domain_test.csv`, runs the frozen model, reports the same metrics separately (never mixed into the training metrics).

**GATE:** paste the split function specifically, and the final metrics table. If accuracy >97%, stop and check for leakage before continuing.

---

## Phase R4 — Swap the Heuristic for the Trained Classifier

**Create:** `app/services/classifier_inference_service.py` — loads `app/ml/model_artifact.joblib` once at import time, exposes `predict_edge_probability(features: dict) -> float`.

**Modify (surgically):** `app/services/relationship_inferencer.py`. Everything stays except one thing:
- **Keep:** the embedding computation, pairwise similarity matrix, cycle-check-on-add logic in `infer_prerequisites` — all of it is fine and reusable.
- **Replace:** the `_determine_direction_and_confidence` method's hardcoded weighted-sum (`0.40 * sim_score + 0.30 * unit_score + ...`) with a call to `ClassifierInferenceService.predict_edge_probability(features)`, where `features` comes from `app/ml/feature_engineering.py::compute_features` (Phase R2) using the same inputs this method already computes (`sim_score`, unit order, etc.).
- **Do not rewrite the whole file.** This is a ~15-line change inside one method.

**GATE:** show the diff of `relationship_inferencer.py` only — confirm nothing else in the file changed.

---

## Phase R5 — Metrics Endpoint

**Create:** `app/api/metrics_router.py` — `GET /api/v1/metrics` returns the contents of `app/ml/metrics_report.json` plus the cross-domain metrics from R3.

**Modify:** `app/main.py` — add one import line + one `app.include_router(metrics_router, ...)` line, matching the existing pattern for the other 8 routers already there. Do not touch any other line in `main.py`.

---

## Phase R6 — Storage Cleanup (requires your explicit go-ahead, not automatic)

Neo4j is a legitimate, standard choice for production knowledge-graph systems generally — that's not in question. It doesn't fit *this* project specifically: each syllabus graph is capped at ~100 nodes, where an in-memory BFS traversal is microseconds and Neo4j's native large-graph query advantage has nothing to act on. It currently no-ops gracefully when unconfigured, so leaving it isn't urgent — but it's worth noting it's write-only in the current code (a sync endpoint pushes data in; nothing anywhere queries it back out), so it isn't functioning as the knowledge graph engine today regardless — the custom in-memory engine already fills that role.

**If you approve:** delete `app/db/neo4j_driver.py`, remove the `sync_to_neo4j` method from `app/services/persistence_service.py`, remove the `/persistence/sync-to-neo4j` endpoint from `app/api/persistence_router.py`, remove `neo4j` from `requirements.txt`.
**If you don't:** leave it — it isn't blocking anything.

**GATE — this phase never runs without your explicit yes**, since it's deletion, not addition.

---

## Phase R7 — Progress Tracking (mostly already done — verify, don't rebuild)

`UserProgress` (status: known/in_progress/blocked) and `POST /persistence/user-progress` already exist and already match the completed/available/locked semantics from the PRD.

**Do:** confirm the frontend's node visual encoding (§11.3 of `KDG_PRD.md`) reads this `status` field correctly — map `known → completed`, `in_progress → available`, `blocked → locked`. No new backend table or endpoint needed unless this mapping doesn't fit once you look at it.

---

## Execution Order

R1 → R2 → R3 → R4 → R5, with R6 only on explicit approval and R7 as a quick verification pass, not new development. Nothing in R2–R5 starts before R1's gate is cleared.
