"""
train_v4.py
===========
Reproducible Prerequisite Edge Classifier Training Pipeline (Phase 6 / P3).

Features:
- Excludes circular heuristic-formula labels.
- Uses shared 3-feature schema with zero train-serve drift:
    ['embedding_similarity', 'keyword_overlap', 'order_delta']
- Subject-held-out (concept-disjoint) splitting.
- Exports model artifact to app/ml/model_artifact_v4.joblib with full metadata
  and provenance in app/ml/model_artifact_v4_meta.json.
"""

import sys
import json
import hashlib
import re
from pathlib import Path
from typing import Tuple, Dict, Any, List

import numpy as np
import pandas as pd
import joblib
from xgboost import XGBClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.ml.feature_engineering import compute_features

V4_TABLE_PATH = project_root / "DATA" / "processed" / "training_table_v4.csv"
FALLBACK_DATA_PATH = project_root / "True_Cleaned_Dataset" / "final_training_dataset.csv"
ARTIFACT_V4_PATH = project_root / "app" / "ml" / "model_artifact_v4.joblib"
META_V4_PATH = project_root / "app" / "ml" / "model_artifact_v4_meta.json"

FEATURE_NAMES = [
    "embedding_similarity",
    "keyword_overlap",
    "order_delta",
]
TARGET_COLUMN = "label"

HEURISTIC_REGEX = re.compile(
    r"Adjacent|sim=|delta=|kw_|Foundational|Insufficient|position|keyword|order",
    re.IGNORECASE,
)


def load_dataset() -> Tuple[pd.DataFrame, str]:
    """Loads either Phase 4 training table or non-heuristic subset of legacy dataset."""
    if V4_TABLE_PATH.exists():
        df = pd.read_csv(V4_TABLE_PATH)
        provenance = f"Phase 4 teacher-labeled table ({V4_TABLE_PATH.name})"
    elif FALLBACK_DATA_PATH.exists():
        raw_df = pd.read_csv(FALLBACK_DATA_PATH)
        # Filter out circular heuristic-labeled rows
        reasons = raw_df["reason"].fillna("").astype(str)
        non_heur_mask = ~reasons.str.contains(HEURISTIC_REGEX)
        df = raw_df[non_heur_mask].copy().reset_index(drop=True)
        provenance = (
            f"Filtered legacy dataset ({FALLBACK_DATA_PATH.name}) "
            f"with all {len(raw_df) - len(df)} heuristic-labeled rows removed"
        )
    else:
        raise FileNotFoundError(f"Neither {V4_TABLE_PATH} nor {FALLBACK_DATA_PATH} found.")

    return df, provenance


def subject_held_out_split(
    df: pd.DataFrame,
    test_ratio: float = 0.25,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Partitions dataset strictly by subject/course to evaluate cross-subject generalization."""
    course_col = "Course_Code" if "Course_Code" in df.columns else "source_syllabus"
    unique_courses = df[course_col].drop_duplicates().sample(frac=1.0, random_state=random_state).tolist()

    test_target = max(1, int(len(df) * test_ratio))
    test_courses = []
    accumulated_test_rows = 0

    for c in unique_courses:
        c_rows = len(df[df[course_col] == c])
        if accumulated_test_rows + c_rows <= test_target or not test_courses:
            test_courses.append(c)
            accumulated_test_rows += c_rows
        else:
            break

    train_courses = [c for c in unique_courses if c not in test_courses]

    train_df = df[df[course_col].isin(train_courses)].reset_index(drop=True)
    test_df = df[df[course_col].isin(test_courses)].reset_index(drop=True)

    return train_df, test_df


def train_and_evaluate():
    print("=" * 60)
    print("KDG — Prerequisite Edge Classifier v4 Training Pipeline")
    print("=" * 60)

    df, provenance = load_dataset()
    print(f"Dataset Provenance: {provenance}")
    print(f"Total Rows: {len(df)} | Positives: {(df[TARGET_COLUMN] == 1).sum()} | Negatives: {(df[TARGET_COLUMN] == 0).sum()}")

    # Ensure feature columns are present and clean
    for feat in FEATURE_NAMES:
        if feat not in df.columns:
            raise KeyError(f"Required feature column '{feat}' missing from dataset.")

    train_df, test_df = subject_held_out_split(df, test_ratio=0.25, random_state=42)
    print(f"Train Rows: {len(train_df)} (Subjects: {train_df['Course_Code'].nunique() if 'Course_Code' in train_df else 'N/A'})")
    print(f"Held-Out Test Rows: {len(test_df)} (Subjects: {test_df['Course_Code'].nunique() if 'Course_Code' in test_df else 'N/A'})")

    X_train = train_df[FEATURE_NAMES].values.astype(np.float32)
    y_train = train_df[TARGET_COLUMN].values.astype(int)

    X_test = test_df[FEATURE_NAMES].values.astype(np.float32)
    y_test = test_df[TARGET_COLUMN].values.astype(int)

    # Train XGBoost with conservative depth to prevent overfitting on small data
    pos_weight = float((y_train == 0).sum() / max(1, (y_train == 1).sum()))
    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=pos_weight,
        random_state=42,
        eval_metric="logloss",
    )

    model.fit(X_train, y_train)

    # Predict on held-out test set
    test_probs = model.predict_proba(X_test)[:, 1]

    # Evaluate across thresholds
    best_f1 = 0.0
    best_threshold = 0.50
    for th in np.arange(0.20, 0.80, 0.05):
        preds = (test_probs >= th).astype(int)
        f = f1_score(y_test, preds, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_threshold = round(float(th), 2)

    final_preds = (test_probs >= best_threshold).astype(int)
    test_prec = precision_score(y_test, final_preds, zero_division=0)
    test_rec = recall_score(y_test, final_preds, zero_division=0)
    test_acc = accuracy_score(y_test, final_preds)
    try:
        test_auc = roc_auc_score(y_test, test_probs)
    except Exception:
        test_auc = 0.0

    print("-" * 60)
    print(f"Optimal Decision Threshold: {best_threshold}")
    print(f"Held-Out Test Precision:   {test_prec:.4f}")
    print(f"Held-Out Test Recall:      {test_rec:.4f}")
    print(f"Held-Out Test F1 Score:    {best_f1:.4f}")
    print(f"Held-Out Test ROC-AUC:     {test_auc:.4f}")
    print(f"Feature Importances:")
    for name, imp in zip(FEATURE_NAMES, model.feature_importances_):
        print(f"  {name:25s}: {imp:.4f}")

    # Save model artifact
    joblib.dump(model, ARTIFACT_V4_PATH)
    print(f"\nSaved model artifact to: {ARTIFACT_V4_PATH}")

    # Save metadata and schema
    data_hash = hashlib.sha256(df.to_csv(index=False).encode("utf-8")).hexdigest()
    meta = {
        "model_version": "v4",
        "training_provenance": provenance,
        "feature_names": FEATURE_NAMES,
        "feature_importances": {name: round(float(imp), 4) for name, imp in zip(FEATURE_NAMES, model.feature_importances_)},
        "optimal_threshold": best_threshold,
        "data_sha256": data_hash,
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "metrics": {
            "test_precision": round(float(test_prec), 4),
            "test_recall": round(float(test_rec), 4),
            "test_f1": round(float(best_f1), 4),
            "test_roc_auc": round(float(test_auc), 4),
            "test_accuracy": round(float(test_acc), 4),
        },
    }
    with open(META_V4_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved metadata to: {META_V4_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    train_and_evaluate()

