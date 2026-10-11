"""
train_v5.py
===========
Reproducible Prerequisite Edge Classifier Training Pipeline (Phase 5).

Key specifications:
- Split by course GROUPS (held-out whole courses: 4 test, 2 validation, 8 train).
- Features via canonical app/ml/features_v5.py.
- PCA-32 fitted strictly on training courses.
- Logistic Regression baseline.
- XGBoost classifier with max_depth in 4-6, early stopping on validation courses.
- Threshold selected on validation courses only.
- Evaluation on test courses: Precision, Recall, F1, PR-AUC.
- Comparison with model_artifact_v4 on identical test rows.
- Exports model_artifact_v5.joblib, pca_artifact_v5.joblib, and model_artifact_v5_meta.json.
- Leaves model_artifact_v4 untouched.
"""

import sys
import json
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
import joblib
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    average_precision_score,
)
from xgboost import XGBClassifier

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.services.embedding_service import LocalEmbeddingService
from app.ml.features_v5 import (
    FEATURE_NAMES,
    compute_diff_prod,
    pair_features,
    set_pca,
    compute_keyword_overlap,
)

DATA_PATH = project_root / "DATA" / "processed" / "training_table_v5.csv"
MODEL_V4_PATH = project_root / "app" / "ml" / "model_artifact_v4.joblib"
MODEL_V4_META_PATH = project_root / "app" / "ml" / "model_artifact_v4_meta.json"
MODEL_V5_PATH = project_root / "app" / "ml" / "model_artifact_v5.joblib"
PCA_V5_PATH = project_root / "app" / "ml" / "pca_artifact_v5.joblib"
META_V5_PATH = project_root / "app" / "ml" / "model_artifact_v5_meta.json"

TEST_COURSES = ["2345113", "23451143", "23461131", "23461142"]
VAL_COURSES = ["2345112", "23461133"]


def compute_file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(project_root)
        ).decode("utf-8").strip()
    except Exception:
        return "UNKNOWN"


def main():
    print("=" * 70)
    print("KDG — Prerequisite Edge Classifier v5 Training Pipeline")
    print("=" * 70)

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Training table not found at {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    data_hash = compute_file_sha256(DATA_PATH)
    git_commit = get_git_commit()

    df["course"] = df["course"].astype(str)
    all_courses = sorted(df["course"].unique().tolist())
    train_courses = [c for c in all_courses if c not in TEST_COURSES and c not in VAL_COURSES]

    print(f"Total rows: {len(df)} across {len(all_courses)} courses")
    print(f"Data SHA-256: {data_hash}")
    print(f"Git commit:   {git_commit}")
    print(f"\nCourse splits:")
    print(f"  Train ({len(train_courses)} courses): {train_courses}")
    print(f"  Val   ({len(VAL_COURSES)} courses):   {VAL_COURSES}")
    print(f"  Test  ({len(TEST_COURSES)} courses):  {TEST_COURSES}")

    train_df = df[df["course"].isin(train_courses)].copy().reset_index(drop=True)
    val_df = df[df["course"].isin(VAL_COURSES)].copy().reset_index(drop=True)
    test_df = df[df["course"].isin(TEST_COURSES)].copy().reset_index(drop=True)

    print(f"\nRow counts:")
    print(f"  Train: {len(train_df)} rows ({int((train_df['label'] == 1).sum())} pos, {int((train_df['label'] == 0).sum())} neg)")
    print(f"  Val:   {len(val_df)} rows ({int((val_df['label'] == 1).sum())} pos, {int((val_df['label'] == 0).sum())} neg)")
    print(f"  Test:  {len(test_df)} rows ({int((test_df['label'] == 1).sum())} pos, {int((test_df['label'] == 0).sum())} neg)")

    # 1. Compute embeddings for all unique concept names (name only)
    print("\nComputing embeddings for unique concept names...")
    all_names = sorted(list(set(df["a_name"].tolist() + df["b_name"].tolist())))
    name_vecs = LocalEmbeddingService.encode_batch(all_names)
    emb_lookup: Dict[str, np.ndarray] = {
        name: vec for name, vec in zip(all_names, name_vecs)
    }
    print(f"Encoded {len(all_names)} unique topic names.")

    # 2. Fit PCA-32 on TRAIN pairs only
    print("\nFitting PCA-32 on training pair embedding difference & product...")
    train_diff_prods = []
    for _, row in train_df.iterrows():
        ea = emb_lookup[row["a_name"]]
        eb = emb_lookup[row["b_name"]]
        dp = compute_diff_prod(ea, eb)
        train_diff_prods.append(dp)
    X_dp_train = np.array(train_diff_prods, dtype=np.float32)

    pca = PCA(n_components=32, random_state=42)
    pca.fit(X_dp_train)
    var_exp = float(np.sum(pca.explained_variance_ratio_))
    print(f"PCA-32 fitted on {len(X_dp_train)} pairs (explained variance ratio: {var_exp:.4f}).")

    # Set PCA globally and save artifact
    set_pca(pca)
    joblib.dump(pca, PCA_V5_PATH)
    print(f"Saved PCA artifact to {PCA_V5_PATH}")

    # 3. Extract canonical 40 features for train, val, test using pair_features
    def build_feature_matrix(subset_df: pd.DataFrame) -> np.ndarray:
        features_list = []
        for _, row in subset_df.iterrows():
            ea = emb_lookup[row["a_name"]]
            eb = emb_lookup[row["b_name"]]
            vec = pair_features(
                a=row["a_name"],
                b=row["b_name"],
                n_topics=row["n_topics"],
                unit_a=row["unit_a"],
                unit_b=row["unit_b"],
                pos_a=row["pos_a"],
                pos_b=row["pos_b"],
                emb_a=ea,
                emb_b=eb,
                pca=pca,
            )
            features_list.append(vec)
        return np.array(features_list, dtype=np.float32)

    print("\nComputing canonical 40-feature matrices via features_v5.pair_features...")
    X_train = build_feature_matrix(train_df)
    y_train = train_df["label"].values.astype(int)

    X_val = build_feature_matrix(val_df)
    y_val = val_df["label"].values.astype(int)

    X_test = build_feature_matrix(test_df)
    y_test = test_df["label"].values.astype(int)

    print(f"Feature matrix shapes: Train={X_train.shape}, Val={X_val.shape}, Test={X_test.shape}")

    # 4. Logistic Regression Baseline
    print("\n--- Training Logistic Regression Baseline ---")
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    lr_val_probs = lr.predict_proba(X_val)[:, 1]
    lr_test_probs = lr.predict_proba(X_test)[:, 1]

    # Best threshold for LR on val
    best_lr_th = 0.5
    best_lr_f1 = 0.0
    for th in np.linspace(0.1, 0.9, 81):
        f = f1_score(y_val, (lr_val_probs >= th).astype(int), zero_division=0)
        if f > best_lr_f1:
            best_lr_f1 = f
            best_lr_th = float(th)

    lr_test_preds = (lr_test_probs >= best_lr_th).astype(int)
    lr_test_prec = precision_score(y_test, lr_test_preds, zero_division=0)
    lr_test_rec = recall_score(y_test, lr_test_preds, zero_division=0)
    lr_test_f1 = f1_score(y_test, lr_test_preds, zero_division=0)
    lr_test_prauc = average_precision_score(y_test, lr_test_probs)

    print(f"Logistic Regression (Val th={best_lr_th:.2f}):")
    print(f"  Test Precision: {lr_test_prec:.4f}")
    print(f"  Test Recall:    {lr_test_rec:.4f}")
    print(f"  Test F1:        {lr_test_f1:.4f}")
    print(f"  Test PR-AUC:    {lr_test_prauc:.4f}")

    # 5. XGBoost with max_depth in 4-6 and early stopping on validation
    print("\n--- Training XGBoost (max_depth 4-6, early stopping on val) ---")
    best_xgb_model = None
    best_xgb_val_prauc = -1.0
    best_depth = None

    for depth in [4, 5, 6]:
        clf = XGBClassifier(
            max_depth=depth,
            learning_rate=0.05,
            n_estimators=300,
            early_stopping_rounds=25,
            eval_metric="logloss",
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
        )
        clf.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        val_probs_d = clf.predict_proba(X_val)[:, 1]
        val_prauc = average_precision_score(y_val, val_probs_d)
        print(f"  max_depth={depth}: Val PR-AUC = {val_prauc:.4f} (best iteration: {clf.best_iteration})")
        if val_prauc > best_xgb_val_prauc:
            best_xgb_val_prauc = val_prauc
            best_xgb_model = clf
            best_depth = depth

    print(f"Selected best XGBoost model: max_depth={best_depth} with Val PR-AUC={best_xgb_val_prauc:.4f}")

    # 6. Choose threshold on validation courses only
    val_probs = best_xgb_model.predict_proba(X_val)[:, 1]
    best_th = 0.50
    best_val_f1 = 0.0
    for th in np.linspace(0.1, 0.9, 81):
        preds = (val_probs >= th).astype(int)
        f = f1_score(y_val, preds, zero_division=0)
        if f > best_val_f1:
            best_val_f1 = f
            best_th = round(float(th), 2)

    val_preds = (val_probs >= best_th).astype(int)
    val_prec = precision_score(y_val, val_preds, zero_division=0)
    val_rec = recall_score(y_val, val_preds, zero_division=0)
    val_prauc = average_precision_score(y_val, val_probs)

    print(f"\nOptimal Decision Threshold on Validation: {best_th:.2f}")
    print(f"  Val Precision: {val_prec:.4f}")
    print(f"  Val Recall:    {val_rec:.4f}")
    print(f"  Val F1:        {best_val_f1:.4f}")
    print(f"  Val PR-AUC:    {val_prauc:.4f}")

    # 7. Evaluate on held-out test courses
    test_probs = best_xgb_model.predict_proba(X_test)[:, 1]
    test_preds = (test_probs >= best_th).astype(int)
    test_prec = precision_score(y_test, test_preds, zero_division=0)
    test_rec = recall_score(y_test, test_preds, zero_division=0)
    test_f1 = f1_score(y_test, test_preds, zero_division=0)
    test_prauc = average_precision_score(y_test, test_probs)

    print(f"\nXGBoost v5 Performance on Held-Out Test Courses (threshold={best_th:.2f}):")
    print(f"  Test Precision: {test_prec:.4f}")
    print(f"  Test Recall:    {test_rec:.4f}")
    print(f"  Test F1:        {test_f1:.4f}")
    print(f"  Test PR-AUC:    {test_prauc:.4f}")

    # 8. Evaluate model_artifact_v4 on the EXACT SAME test rows
    print("\n--- Evaluating baseline model_artifact_v4 on identical test rows ---")
    v4_prec = 0.0
    v4_rec = 0.0
    v4_f1 = 0.0
    v4_prauc = 0.0
    if MODEL_V4_PATH.exists():
        model_v4 = joblib.load(MODEL_V4_PATH)
        v4_th = 0.40
        if MODEL_V4_META_PATH.exists():
            with open(MODEL_V4_META_PATH) as f:
                v4_meta = json.load(f)
                v4_th = v4_meta.get("optimal_threshold") or v4_meta.get("threshold", 0.40)

        # Build v4 feature matrix: ['embedding_similarity', 'keyword_overlap', 'order_delta']
        v4_feats = []
        for _, row in test_df.iterrows():
            ea = emb_lookup[row["a_name"]]
            eb = emb_lookup[row["b_name"]]
            na = float(np.linalg.norm(ea))
            nb = float(np.linalg.norm(eb))
            sim = float(np.dot(ea, eb) / (na * nb)) if na > 1e-9 and nb > 1e-9 else 0.0
            kw = compute_keyword_overlap(row["a_name"], row["b_name"])
            delta = float(row["pos_b"] - row["pos_a"])
            v4_feats.append([sim, kw, delta])

        X_test_v4 = np.array(v4_feats, dtype=np.float32)
        v4_test_probs = model_v4.predict_proba(X_test_v4)[:, 1]
        v4_test_preds = (v4_test_probs >= v4_th).astype(int)

        v4_prec = precision_score(y_test, v4_test_preds, zero_division=0)
        v4_rec = recall_score(y_test, v4_test_preds, zero_division=0)
        v4_f1 = f1_score(y_test, v4_test_preds, zero_division=0)
        v4_prauc = average_precision_score(y_test, v4_test_probs)

        print(f"model_artifact_v4 (threshold={v4_th}):")
        print(f"  Test Precision: {v4_prec:.4f}")
        print(f"  Test Recall:    {v4_rec:.4f}")
        print(f"  Test F1:        {v4_f1:.4f}")
        print(f"  Test PR-AUC:    {v4_prauc:.4f}")
    else:
        print("model_artifact_v4 not found; skipping v4 comparison.")

    # 9. Save artifacts
    # Attach pca model attribute to estimator for convenience
    best_xgb_model.pca_ = pca
    joblib.dump(best_xgb_model, MODEL_V5_PATH)
    print(f"\nSaved XGBoost v5 artifact to {MODEL_V5_PATH}")

    meta_v5: Dict[str, Any] = {
        "model_version": "v5",
        "provenance": "DATA/processed/training_table_v5.csv with 3:1 negative ratio from dual-run teacher labels",
        "embedding_model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "feature_list": FEATURE_NAMES,
        "threshold": best_th,
        "data_hash": data_hash,
        "git_commit": git_commit,
        "best_depth": best_depth,
        "train_courses": train_courses,
        "val_courses": VAL_COURSES,
        "test_courses": TEST_COURSES,
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "test_rows": len(test_df),
        "metrics": {
            "val_precision": round(float(val_prec), 4),
            "val_recall": round(float(val_rec), 4),
            "val_f1": round(float(best_val_f1), 4),
            "val_pr_auc": round(float(val_prauc), 4),
            "test_precision": round(float(test_prec), 4),
            "test_recall": round(float(test_rec), 4),
            "test_f1": round(float(test_f1), 4),
            "test_pr_auc": round(float(test_prauc), 4),
        },
        "v4_comparison_test": {
            "v4_precision": round(float(v4_prec), 4),
            "v4_recall": round(float(v4_rec), 4),
            "v4_f1": round(float(v4_f1), 4),
            "v4_pr_auc": round(float(v4_prauc), 4),
        },
    }

    with open(META_V5_PATH, "w", encoding="utf-8") as f:
        json.dump(meta_v5, f, indent=2)
    print(f"Saved metadata to {META_V5_PATH}")

    print("\n" + "=" * 70)
    print("V4 vs V5 TEST COMPARISON SUMMARY")
    print("=" * 70)
    print(f"{'Metric':<15} | {'Model v4':<12} | {'Model v5':<12} | {'Delta':<10}")
    print("-" * 55)
    print(f"{'Precision':<15} | {v4_prec:<12.4f} | {test_prec:<12.4f} | {test_prec - v4_prec:+10.4f}")
    print(f"{'Recall':<15} | {v4_rec:<12.4f} | {test_rec:<12.4f} | {test_rec - v4_rec:+10.4f}")
    print(f"{'F1':<15} | {v4_f1:<12.4f} | {test_f1:<12.4f} | {test_f1 - v4_f1:+10.4f}")
    print(f"{'PR-AUC':<15} | {v4_prauc:<12.4f} | {test_prauc:<12.4f} | {test_prauc - v4_prauc:+10.4f}")
    print("=" * 70)


if __name__ == "__main__":
    main()

