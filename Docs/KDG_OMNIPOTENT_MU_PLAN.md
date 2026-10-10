# KDG — Omnipotent MU Model: Execution Plan

**This file is self-contained.** If your context window truncates earlier turns, everything
needed to continue correctly is here — re-read this file, not prior conversation, before
acting.

---

## 0. Doctrine (unchanged from the whole project — recap, do not re-derive)

One trained classifier (currently XGBoost) predicts "is A a prerequisite of B?" —
everything else (sequence, bottlenecks, missing prereqs) is deterministic graph algorithms
on top of its predicted edges. Accuracy is measured on the classifier only. An OCR/LLM API
may assist ingestion and labeling — it never replaces the classifier as the prediction
mechanism. This is a hard grading condition, not a preference.

## 1. Scope of THIS plan — read before doing anything

**In scope:** making the MU-only model as strong as possible — full MU corpus coverage,
real API-assisted labeling at scale, hyperparameter tuning, safe feature enrichment,
graph-algorithm robustness hardening.

**Explicitly OUT of scope for this plan — do not pull these in, they are separate,
later workstreams:**
- Cross-domain/international diversification (comes after this plan, not during)
- Quiz system, continuous-learning auto-retrain pipeline
- Frontend redesign
If a step here seems to justify touching any of the above, STOP and ask instead of
expanding scope.

## 2. Ground Truth Check — ALWAYS run this first, never assume prior numbers are current

Before any phase, run and report:
```
wc -l Cleaned_Files/final_training_dataset.csv (or whatever the current master dataset is)
ls app/ml/*.joblib
cat app/ml/metrics_report.json
```
State the actual current row count, current frozen model file, and current metrics.
Do not proceed using a row count or metric number from memory/conversation — verify fresh.

---

## Phase M1 — Full MU Corpus Expansion

**Goal:** all MU branches, all semesters (I through VIII), not just the current subset.

1. Inventory: list every MU syllabus PDF available, cross-check against what's already
   processed (by filename) to avoid reprocessing.
2. Run the existing fixed extractor (7-digit course code regex + the VSEC/AEC/BSC-style
   fallback patterns already added) unchanged on new files first.
3. For any file yielding 0 topics: diagnose per the established method (raw char count →
   LIKELY_SCANNED vs PARSER_MISMATCH) before touching any regex. Only add a new fallback
   pattern if a genuinely new course-code format is confirmed — do not guess.
4. Reserve nothing new as cross-domain test data in this phase — that set is frozen from
   earlier work, do not add to or modify `cross_domain_test.csv`.

**GATE:** report per-file topic counts for all new files. Flag zero-topic files before
proceeding to labeling — do not silently drop them.

---

## Phase M2 — Real API-Assisted Labeling at Full Scale

**Goal:** replace the old heuristic threshold-rule labeling with real LLM-API-generated
label suggestions + reasoning, applied across the full expanded corpus.

1. Batch candidate pairs into groups of ~20-30 per API call (quota conservation) — never
   one call per pair.
2. For each pair, r
3. Build a human-review sample: aequest: suggested label (0/1) + one-line reason, using the fixed rule:
   "label 1 only if understanding concept_b directly and unavoidably requires concept_a —
   not merely commonly taught before it." flat random sample sized proportionally to new volume
   (roughly 10% of new rows, minimum 100), written with a blank confirmed_label column and
   ai_suggested_label kept visible separately.
4. **STOP.** Do not finalize any label. Wait for the human review + agreement rate.

**GATE:** ≥90% agreement required before this batch's labels are considered final and
merged into the master dataset. Below that, report the mismatch pattern and wait for a
decision — do not auto-relabel or auto-discard.

---

## Phase M3 — Hyperparameter Tuning

**Goal:** improve the XGBoost model itself, not just the data.

1. Using the existing concept-disjoint train/val split (do not create a new split
   methodology — reuse the proven one), run a grid or randomized search over:
   n_estimators, max_depth, learning_rate, min_child_weight, subsample.
2. Select the best combination by validation F1, not training accuracy.
3. Evaluate the tuned model on the untouched test set AND on cross_domain_test.csv.
4. Save as a new versioned artifact (e.g. model_artifact_v4.joblib) — do NOT overwrite
   the currently-frozen production artifact.

**GATE:** show a side-by-side metrics table — current frozen model vs. newly tuned model,
on both in-domain test and cross-domain test. Only promote if genuinely better on held-out
test data, not validation alone. Promotion requires explicit user approval.

---

## Phase M4 — Feature Enrichment (only after M1-M3 are stable)

**Goal:** add features previously deferred for time, now that the dataset and model are
in better shape.

1. Add to the SAME shared feature_engineering.py used by both training and inference
   (never a second copy):
   - A cross-encoder or richer semantic similarity score, alongside (not replacing) the
     existing embedding_similarity
   - A structural feature reflecting module/unit depth if reliably extractable
2. Retrain with the same tuned hyperparameters from M3. Compare against M3's result on
   the same test + cross-domain sets.

**GATE:** only keep new features if they measurably improve test metrics — report the
before/after honestly, including if a feature made no difference or hurt performance.

---

## Phase M5 — Kahn's Algorithm & Graph Robustness Hardening

**Goal:** the graph layer is deterministic — but "deterministic" only helps if every edge
case is actually tested, not just the happy path.

1. Add unit tests for: disconnected components, a single-node graph, an empty graph,
   multiple simultaneous cycles in the predicted edge set, and the existing cycle-breaking
   logic (keep higher-confidence edge) under a case with 3+ mutually conflicting edges.
2. Verify — end to end, not just backend — that the frontend's rendered sequence order
   exactly matches the backend's computed topological order. A correct backend result
   displayed in a subtly wrong order is indistinguishable from a bug in a live demo; check
   this explicitly, don't assume it's fine because the backend test passes.

**GATE:** all new tests pass; frontend/backend order match is confirmed with an actual
screenshot or printed comparison, not a claim.

---

## Anti-Hallucination Rules (apply at every phase, every step)

- Never report a metric without having actually run the code that produces it.
- Never claim a model is "better" without a side-by-side test-set (not just validation)
  comparison table.
- Never skip Phase M2's human-verification gate, regardless of how good the API-generated
  labels look — this has failed silently before in this project when skipped.
- Never expand into the explicitly out-of-scope items in Section 1 without being asked.
- Never overwrite a frozen/production artifact — new versions get new filenames.
- If uncertain about current state, re-run Section 2's ground-truth check — do not assume.

---

## Reporting Format

End every phase with:
```
PHASE [M#] COMPLETE — [key numbers/evidence]. Awaiting go-ahead for next phase.
```
or
```
PHASE [M#] HALTED — [exact reason]. Awaiting decision.
```
