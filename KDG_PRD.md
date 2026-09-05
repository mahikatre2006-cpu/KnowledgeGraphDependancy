# Knowledge Dependency Graph (KDG) — Product Requirements Document

**Version:** 1.0 | **Status:** Build-Ready | **Audience:** Engineering (Siddhesh + team) & AI IDE agents | **Type:** AIML Mini-Project | **Date:** July 2026

---

## 0. Doctrine (Non-Negotiable)

> **One sentence:** KDG is a trained edge-classifier feeding deterministic graph algorithms — it does not "AI-generate" a sequence, it predicts edges and computes the rest exactly.

- **Only one thing is learned: does A → B?** Everything downstream (sequence, bottlenecks, gaps) is exact graph math on top of that predicted edge set. Never train a model to output "the sequence" directly — that's reinventing topological sort with noise, and it can't be validated with accuracy/F1/confusion-matrix the way a professor expects.
- **Accuracy is measured on the classifier, not the pipeline.** The viva defense is: "our model has 87% F1 on prerequisite prediction; sequencing and bottlenecks are provably correct graph algorithms given that predicted graph." This is the single most important sentence in this document — say it in the demo.
- **3000-row dataset is the hard gate.** Nothing else matters if this isn't real, labeled, and leak-free (split by concept, not row).
- **CPU-only, no GPU dependency.** XGBoost/RF on engineered features, not a fine-tuned transformer.
- **MVP excludes LLM-based inference augmentation.** The second reference doc's "LLM reasoning per topic pair + ConceptNet + ACM maps" is a *v2 accuracy booster*, not an MVP requirement — it adds an ungradeable black box exactly where the professor wants a gradeable trained model. Keep the LLM (if used at all) to concept-extraction text cleanup only, never to prerequisite-edge decisions in the graded pipeline.

### What KDG Is NOT (MVP scope guard)

- Not a study-planner / exam-scheduler app (that's the ASCEND/exam-prep feature set — future scope)
- Not a quizzing or spaced-repetition system
- Not a multi-syllabus cross-course platform
- Not a gamified engagement product
- It is: **upload syllabus → trained model predicts prerequisite edges → graph algorithms output sequence, gaps, bottlenecks → visualize → export.**

---

## 1. Problem Statement & Goals

**Input:** a university syllabus (PDF/text).
**Output:** three artifacts, all derived from one predicted directed graph:
1. Optimal learning sequence (topological order)
2. Missing prerequisites (concepts the syllabus assumes but never teaches)
3. Bottleneck concepts (topics that unlock the most downstream learning)

**Primary goal (grading):** a classifier trained from scratch on ≥3000 rows, with full validation metrics, feeding a correct and explainable graph-algorithm layer.
**Secondary goal (demo):** a clean, interactive, working end-to-end product — not just a notebook.

---

## 2. System Architecture

```
[Frontend: React + Vite + Tailwind]
   Upload → Graph View (react-flow) → Sequence List → Bottleneck Panel → Metrics Dashboard → Export
        |
        v  (multipart POST /api/v1/syllabus/analyze)
[Backend API: FastAPI]
   ├── Concept Extraction Module      — parses syllabus text into a clean concept list
   ├── Feature Engineering Module     — builds the (concept_a, concept_b) feature vector for every candidate pair
   ├── ML Inference Module            — loads frozen XGBoost model, predicts edge probability per pair
   ├── Graph Construction Module      — custom Python adjacency-list DAG engine (already implemented, tested — networkx swap optional, not required)
   ├── Graph Algorithms Module
   │      - Kahn's algorithm           → learning sequence
   │      - Downstream-reachability + out-degree → bottleneck ranking
   │      - Non-edge threshold scan    → missing prerequisites
   └── Report Generator                — PDF/JSON export
        |
        v
[Supabase (Postgres)] — syllabi, extracted concepts, predicted graphs, model metrics, reports, user progress
[Neo4j] — optional, disabled by default. Not required at ≤100-node graph scale; revisit only if a future version needs persistent cross-course graphs at real scale.
```

**Offline / training-time path (not part of the request pipeline):**
```
Labeled dataset (≥3000 rows, CSV)
   → Feature engineering (same functions as inference, imported as a shared module)
   → Train/val/test split (70/15/15, split BY CONCEPT)
   → Train: Logistic Regression baseline → XGBoost primary
   → 5-fold CV → metrics table → freeze model artifact (model.pkl / model.json)
```

This offline/online split is deliberate: **the feature-engineering code must be a single shared module imported by both the training script and the FastAPI inference module.** Divergence between train-time and inference-time features is the #1 way these projects silently break — flag this in code review, don't wait for it to show up as a bug.

---

## 3. MVP Scope (Ship This)

| # | Feature | Why it's MVP | Component |
|---|---|---|---|
| 1 | Syllabus upload (PDF + plain text) | Core input | Frontend + FR1 |
| 2 | Concept extraction (rule-based: heading/bullet parsing + noun-phrase extraction) | No LLM dependency risk under deadline | Backend |
| 3 | Trained prerequisite classifier (XGBoost, ≥3000 rows) | This IS the graded deliverable | ML module |
| 4 | Graph construction (custom adjacency-list engine — already implemented) | Deterministic, cheap | Backend |
| 5 | Topological sort → sequence | FR5 | Graph module |
| 6 | Missing-prerequisite detection (classifier run on non-edges, threshold flag) | FR6 | Graph module |
| 7 | Bottleneck ranking (betweenness + out-degree) | FR7 | Graph module |
| 8 | Interactive graph visualization (react-flow, ≤100 nodes) | FR8, demo credibility | Frontend |
| 9 | Metrics dashboard (accuracy, precision, recall, F1, confusion matrix, ROC-AUC) | FR9 — this is what proves "trained from scratch" | Frontend |
| 10 | Export report (PDF/JSON) | FR10 | Backend |
| 11 | Mark concept as completed + visual progress state on graph | FR11, FR12 | Frontend + Backend |

**Explicitly cut from MVP** (all valid ideas from the second reference doc — deferred to §15 Future Scope, not deleted):
OCR for scanned syllabi · LLM-per-pair reasoning · ConceptNet/ACM external graph fusion · exam-date study scheduler · time-estimation per topic · topic-specific study tips · adaptive re-planning · diagnostic quizzing · spaced repetition · resource recommendation · cross-course linking · exam-frequency weighting.

Reason for the cut, stated once so it doesn't need re-litigating: **every one of those is either (a) a second product built on top of a working graph, or (b) reintroduces an ungraded LLM black box into the one component that must be a transparently trained, validated model.** Build the graph engine first; it is the entire grade.

---

## 4. Dataset Construction (Phase 1 — do this first, it blocks everything)

- **Size:** ≥3000 labeled concept-pair rows (hard professor requirement).
- **Schema:** `concept_a, concept_b, embedding_similarity, order_delta, domain_match, difficulty_delta, keyword_overlap, label`
- **Sources:** real syllabi across 3–5 CS/IT subjects (DBMS, OS, DSA, CN, Web Dev — matches your own coursework, so labeling is fast and defensible in viva), textbook TOC ordering, ACM/IEEE curriculum guideline structure.
- **Labeling protocol (write this down before labeling starts, one page, fixed rules):** what counts as "A is a prerequisite of B" — direct conceptual dependency only, not "commonly taught before." Include hard negatives: same-domain pairs with no dependency (e.g., "Normalization" / "Indexing" — related, not prerequisite).
- **Labeling workflow — AI-assisted, human-verified (not full manual, not full automated):**
  1. Generate candidate pairs per subject (extraction script — see §12 Roadmap, Phase 1).
  2. Get a suggested label + one-line reason from an LLM (Claude/GPT) applying the same fixed rule above.
  3. Human review a sample, not the full set: every hard-negative pair, plus a random ~20–25% slice of the rest. If team agreement with the AI labels is ≥90% on that sample, accept the remainder; if lower, widen the sample and re-check.
  4. Document this explicitly in the submission as **AI-assisted labeling with human-verified sampling** — a real, named weak-supervision technique, not a shortcut to hide.
- **Balance:** roughly balanced positive/negative classes.
- **No cycles:** validate at dataset level — reject any (A,B)+(B,A) both-positive pair.
- **Split:** 70/15/15 by **concept**, not row — a concept must not appear in both train and test, or you leak.
- **Cross-domain held-out test set (generalization check):** separately from the main dataset, collect 200–300 additional labeled rows from 2–3 non-IT departments (e.g. Mechanical, Civil, Electronics). These rows **never enter training** — they exist only to measure how much accuracy drops outside the training domain. Report as a distinct metric: "X% F1 in-domain vs. Y% F1 cross-domain." This is what backs any claim that KDG generalizes beyond IT syllabi — an evidence-based gap, not an assumption.

---

## 5. ML Component

| Approach | Verdict |
|---|---|
| Logistic Regression / Random Forest | Baseline — train first, cheap sanity check |
| **XGBoost** | **Primary model** — best accuracy/effort ratio at 3000-row scale, CPU-only |
| GNN (GraphSAGE/GCN) | Explicitly out of MVP — needs more data than you have, hard to debug under deadline. Mention as future scope in viva, do not attempt it under time pressure. |

**Features:** embedding similarity (sentence-transformers or TF-IDF cosine) · syllabus order-delta · concept difficulty-tag delta (if tagged) · keyword/n-gram overlap · domain-match flag.

**Evaluation:** report the full table — accuracy, precision, recall, F1, confusion matrix, ROC-AUC — plus 5-fold CV on the training set before final test evaluation. One accuracy number alone does not satisfy "validate accuracy"; the professor is checking for methodology, not a scalar.

**On "100% accuracy":** do not chase this number — a model reporting 100% on a 3000-row human-labeled dataset reads as leakage or an evaluation bug to anyone who checks, and it will get you the opposite of the grade you want. What you want in the demo is: a strong, honestly-reported metrics table (likely 82–92% range is very credible for this task) plus a graph layer that is provably 100% correct, because topological sort and centrality are deterministic. **Frame it exactly that way**: "the graph algorithms are 100% correct by construction; the classifier's honestly-reported accuracy is the interesting number."

**On generalization claims:** the classifier trains primarily on IT/CS-adjacent subjects (fastest, most reliable labeling). Features are intentionally structural (order-delta, embedding similarity, domain-match) rather than IT-vocabulary-locked, which should transfer reasonably across departments — but don't assert "works on any syllabus" without evidence. Report in-domain vs. cross-domain metrics side by side (§4) and let that number make the claim.

---

## 6. Graph Algorithm Layer (deterministic — implement, don't train)

- **Sequencing:** Kahn's algorithm on the predicted DAG. If a cycle is detected post-prediction (classifier predicted both directions positive above threshold), break it by keeping the higher-confidence edge — log this, show it in the demo as a robustness feature, not a bug.
- **Missing prerequisites:** run the classifier on all concept pairs *not* already connected in the syllabus-derived graph; flag pairs above a confidence threshold (tune this — start at 0.75) as "assumed but not taught."
- **Bottlenecks:** betweenness centrality (sits on the most learning paths) and out-degree (unlocks the most downstream topics) — rank and surface top-N.

---

## 7. Functional Requirements

| ID | Requirement |
|---|---|
| FR1 | Accept syllabus upload (PDF/plain text) |
| FR2 | Extract concept/topic list from syllabus |
| FR3 | Predict prerequisite relationships via trained classifier |
| FR4 | Construct directed concept graph from predicted edges |
| FR5 | Output learning sequence via topological sort |
| FR6 | Detect and display missing prerequisites |
| FR7 | Identify and rank bottleneck concepts |
| FR8 | Visualize dependency graph interactively |
| FR9 | Display classifier evaluation metrics (accuracy, F1, confusion matrix, ROC-AUC) |
| FR10 | Export sequence/report (PDF/JSON) |
| FR11 | User can mark a concept as completed |
| FR12 | System visually distinguishes completed / in-progress / available / locked concepts on the graph |

## 8. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR1 | Concept extraction + prediction for ~30–50 topics completes in <10s |
| NFR2 | Accuracy reported with train/test split, not training accuracy alone |
| NFR3 | Graph stays readable/interactive up to ~100 nodes |
| NFR4 | CPU-only inference, no GPU dependency |
| NFR5 | ML layer, graph-algorithm layer, and API layer are separately testable modules |
| NFR6 | Feature-engineering code is a single shared module — no train/inference drift |

---

## 9. API Contract

| Method | Route | Body | Response |
|---|---|---|---|
| `POST` | `/api/v1/syllabus/upload` | `{ file: PDF/text }` | `{ syllabus_id, concepts[] }` |
| `POST` | `/api/v1/syllabus/{id}/analyze` | — | `{ graph_id, sequence[], bottlenecks[], missing_prereqs[] }` |
| `GET` | `/api/v1/graph/{graph_id}` | — | `{ nodes[], edges[] }` (react-flow shape) |
| `GET` | `/api/v1/graph/{graph_id}/metrics` | — | `{ accuracy, precision, recall, f1, roc_auc, confusion_matrix }` |
| `GET` | `/api/v1/graph/{graph_id}/export?format=pdf|json` | — | file stream |
| `GET` | `/health` | — | `{ status, model_version }` |

---

## 10. Database Schema (Supabase / Postgres)

```
syllabi
  id              uuid PK
  raw_text        text
  uploaded_at     timestamp

concepts
  id              uuid PK
  syllabus_id     uuid REFERENCES syllabi(id)
  label           text
  order_index     integer

predicted_edges
  id              uuid PK
  syllabus_id     uuid REFERENCES syllabi(id)
  source_id       uuid REFERENCES concepts(id)
  target_id       uuid REFERENCES concepts(id)
  probability     float
  is_missing_prereq boolean DEFAULT false

model_runs
  id              uuid PK
  model_version   text
  accuracy        float
  precision       float
  recall          float
  f1              float
  roc_auc         float
  confusion_matrix jsonb
  trained_at      timestamp

reports
  id              uuid PK
  syllabus_id     uuid REFERENCES syllabi(id)
  file_url        text
  generated_at    timestamp

user_progress   (already implemented — app/db/postgres_models.py)
  id              string PK
  user_id         string REFERENCES users(id)
  concept_id      string
  status          string   -- "known" | "in_progress" | "blocked", default "known"
  updated_at      timestamp
```

**Note:** `user_progress` and its save endpoint (`POST /persistence/user-progress`) already exist in the codebase — no new table or endpoint needed. See §11.5.

---

## 11. UI/UX Workflow & Visualization Design

### 11.1 Feasibility & Rendering Approach

Reference: a BirdsEyes-style dark, glowing, force-directed node graph. The aesthetic is achievable within KDG's constraints (≤100 nodes, must run smoothly on any device) — but recreate the *look*, not the likely *rendering tech*. BirdsEyes' bloom/glow and ambient starfield strongly suggest a WebGL/3D pipeline — heavy on GPU, higher stutter risk on budget devices, and unnecessary complexity for a 100-node academic tool.

**Chosen approach — SVG-based, no new stack:**
- **Layout:** `d3-force` (forceSimulation + forceLink + forceManyBody + forceCenter) computes node positions — pure math, no rendering cost, ~30kb
- **Rendering:** react-flow (already in stack) renders nodes/edges as SVG; pan/zoom via hardware-accelerated CSS transforms
- **Glow:** CSS `box-shadow` on nodes, or one reusable SVG `<feGaussianBlur>` filter for edges — visually close to bloom, a fraction of the GPU cost
- **Ambient background:** a single static tiled dot-pattern SVG/PNG, not a live particle simulation — near-identical look, zero render cost
- **Bottom detail sheet:** CSS transition or Framer Motion slide-up panel

This gets ~90% of the visual identity at a fraction of the compute cost, and stays inside the already-planned stack.

### 11.2 View Modes

Segmented control at the top of the screen (mirrors BirdsEyes' SOLAR/GRAPH/LIST switcher):

| Mode | Shows |
|---|---|
| **Graph** | Force-directed DAG, primary view |
| **Sequence** | Ordered list mirroring topological sort; tap an item to jump to it in Graph view |
| **Bottlenecks** | Ranked panel of top-N high-centrality concepts |

### 11.3 Node Visual Encoding

| Signal | Encoding |
|---|---|
| Sequence position | Color gradient — cool (early/foundational) → warm (late/advanced) |
| Bottleneck concept | Persistent ring/halo (same visual language as BirdsEyes' "focused" double-ring) |
| Missing prerequisite | Dashed ring + amber tint + small warning icon |
| Completed | Solid fill + checkmark icon — maps to `status: known` |
| In progress | Partial fill / pulsing ring — maps to `status: in_progress` |
| Available now | Normal glow — no progress record yet, but all prerequisites are `known` (computed client-side, not stored) |
| Locked | Dimmed/desaturated — maps to `status: blocked`, or prerequisites not yet `known` |

"Available now" is the one state with no stored record — it's derived by checking that every prerequisite of an untouched concept has `status: known`.

### 11.4 Screen-by-Screen Workflow

1. **Upload** — drag-drop PDF/text, subject name field, "Analyze" button
2. **Graph View** — tapping a node slides up a bottom detail sheet (mirrors BirdsEyes):
   - Concept name + subject tag
   - Sequence position ("Step 6 of 24")
   - Prerequisites list (tap to jump to that node)
   - What it unlocks downstream (explainability — why it's ranked where it is)
   - Confidence score, if it's a missing/inferred prerequisite
   - **"Mark as Completed"** toggle button
3. **Sequence View** — same data as a scrollable ordered list; each row shows lock/available/completed state; tap to jump into Graph view centered on that node
4. **Bottlenecks Panel** — top-N ranked list with centrality/out-degree score, tap to highlight on graph
5. **Missing Prerequisites Panel** — flagged pairs with confidence score and a "why" tooltip (the feature values driving the flag)
6. **Metrics Dashboard** — full metrics table + confusion matrix heatmap — this is your viva slide, build it well
7. **Export** — download PDF/JSON report

### 11.5 Progress Tracking

- **Already implemented** — `user_progress` table (§10) and `POST /persistence/user-progress` endpoint exist in the current codebase. No new table or endpoint needed.
- Frontend maps the 4 visual states to this schema: `known → completed`, `in_progress → in progress`, `blocked → locked`, no record + prerequisites all `known` → `available` (computed, not stored).
- Remaining work is frontend-only: wire the graph's node rendering to read `status` per concept and apply the encoding in §11.3.

---

## 12. Roadmap (condensed — 6 weeks)

| Phase | Weeks | Deliverable |
|---|---|---|
| 1. Dataset | 1–2 | ≥3000 labeled rows, validated (no cycles, balanced, hard negatives) |
| 2. Features | 2 | Shared feature-engineering module + training CSV |
| 3. Model | 3 | LogReg baseline → XGBoost, CV'd, full metrics table, frozen artifact |
| 4. Graph layer | 3–4 | Topo sort, centrality, missing-prereq scan implemented + unit tested |
| 5. Backend API | 4 | FastAPI endpoints wired to model + graph modules |
| 6. Frontend | 4–5 | Upload, graph view, sequence, bottleneck, metrics dashboard |
| 7. Testing | 5 | DAG-guarantee tests, held-out test set validation, e2e real-syllabus run |
| 8. Demo prep | 6 | 2–3 real syllabus demo cases, metrics report for viva |

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Labeling inconsistency | Fixed one-page labeling protocol before Phase 1 |
| Train/test leakage | Split by concept, never by row |
| Cyclic predicted edges break topo sort | Validate DAG property post-prediction; break ties by confidence |
| Weak features → low accuracy | Prioritize embedding quality over model complexity; don't over-tune under deadline |
| Messy graph on demo syllabus | Cap displayed nodes (~30–50), pre-test with real syllabi before demo day |
| Chasing "100% accuracy" reads as leakage in viva | Report honest metrics on the classifier; claim 100%-correctness only for the deterministic graph layer |

---

## 14. Definition of Done (MVP)

- [ ] Classifier trained from scratch on ≥3000 rows, full metrics table reported (not accuracy alone)
- [ ] End-to-end live: syllabus upload → sequence + missing prerequisites + bottlenecks
- [ ] Interactive graph renders and stays readable at demo scale
- [ ] ML layer / graph layer / API layer independently unit-tested
- [ ] Trained model vs. deterministic-algorithm distinction is one sentence you can say clearly in viva
- [ ] Users can mark concepts completed and see locked/available/completed state reflected on the graph
- [ ] Cross-domain generalization gap measured and reported (in-domain vs. cross-domain metrics)

---

## 15. Future Scope (v2 — do not build now)

Pulled from the full product-vision reference, ordered by leverage:

1. **LLM-assisted prerequisite inference** (per-pair reasoning + ConceptNet/ACM fusion) to boost classifier recall on sparse syllabi
2. **OCR ingestion** for scanned syllabi
3. **Exam-prep scheduler** — day-by-day plan respecting the dependency graph + exam date
4. **Diagnostic quizzing** feeding back into a per-user weakness vector (this is effectively the ASCEND model — a full second product, not a mini-project increment)
5. **Spaced repetition layer** for already-covered topics
6. **Cross-course linking** — shared-prerequisite detection across multiple uploaded syllabi
7. **Exam pattern analysis** — weight bottlenecks by historical exam frequency
8. **Resource recommendation** — link concepts to textbook sections/videos

None of these are needed to pass this project. They're here so the viva answer to "what's next" is a roadmap, not an improvisation.

---

*Document synthesized from: KDG SRS (depth analysis), full product-vision feature reference, and ASCEND PRD (structural reference) — July 2026.*
