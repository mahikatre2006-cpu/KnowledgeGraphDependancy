"""
train_classifier.py
===================
Prerequisite Edge Classifier Training Pipeline

- Evaluates models using concept-disjoint train/validation/test splits.
- Trains baseline Logistic Regression and primary XGBoost classifier with 5-fold cross-validation.
- Saves model artifact to app/ml/model_artifact.joblib and metrics to app/ml/metrics_report.json.
"""

import sys
import json
from pathlib import Path
from typing import Tuple, Dict, Any, List

import numpy as np
import pandas as pd
import joblib

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier

project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

DATA_PATH = Path(project_root) / "Cleaned_Files" / "labeling_dataset.csv"
if not DATA_PATH.exists():
    DATA_PATH = Path(project_root) / "data" / "labeling_dataset.csv"
ARTIFACT_PATH = Path(project_root) / "app" / "ml" / "model_artifact.joblib"
METRICS_PATH = Path(project_root) / "app" / "ml" / "metrics_report.json"

FEATURE_COLUMNS = [
    "embedding_similarity",
    "order_delta",
    "domain_match",
    "keyword_overlap",
]
TARGET_COLUMN = "label"


def concept_aware_split(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Partitions dataset into train, val, and test splits strictly by concept groups.
    Guarantees train_concepts ∩ test_concepts = ∅ and train_concepts ∩ val_concepts = ∅.
    """
    # Since candidate pairs are strictly localized by Course_Code, partitioning by Course_Code
    # naturally produces disjoint concept sets across subjects without breaking pairs.
    unique_courses = df["Course_Code"].drop_duplicates().sample(frac=1.0, random_state=random_state).tolist()
    
    total_rows = len(df)
    train_target = int(total_rows * train_ratio)
    val_target = int(total_rows * val_ratio)
    
    train_courses = []
    val_courses = []
    test_courses = []
    
    current_train = 0
    current_val = 0
    
    for course in unique_courses:
        course_rows = len(df[df["Course_Code"] == course])
        if current_train + course_rows <= train_target or not train_courses:
            train_courses.append(course)
            current_train += course_rows
        elif current_val + course_rows <= val_target or not val_courses:
            val_courses.append(course)
            current_val += course_rows
        else:
            test_courses.append(course)
            
    train_df = df[df["Course_Code"].isin(train_courses)].reset_index(drop=True)
    val_df = df[df["Course_Code"].isin(val_courses)].reset_index(drop=True)
    test_df = df[df["Course_Code"].isin(test_courses)].reset_index(drop=True)

    # Formal Leakage Verification
    train_concepts = set(train_df["concept_a"]).union(set(train_df["concept_b"]))
    val_concepts = set(val_df["concept_a"]).union(set(val_df["concept_b"]))
    test_concepts = set(test_df["concept_a"]).union(set(test_df["concept_b"]))

    # If any overlapping concept exists between train and test/val, drop overlapping rows from test/val
    val_overlap = train_concepts.intersection(val_concepts)
    test_overlap = train_concepts.intersection(test_concepts)

    if val_overlap:
        val_df = val_df[~val_df["concept_a"].isin(val_overlap) & ~val_df["concept_b"].isin(val_overlap)].reset_index(drop=True)
    if test_overlap:
        test_df = test_df[~test_df["concept_a"].isin(test_overlap) & ~test_df["concept_b"].isin(test_overlap)].reset_index(drop=True)

    # Re-verify absolute disjointness
    final_train_c = set(train_df["concept_a"]).union(set(train_df["concept_b"]))
    final_test_c = set(test_df["concept_a"]).union(set(test_df["concept_b"]))
    final_val_c = set(val_df["concept_a"]).union(set(val_df["concept_b"]))

    assert final_train_c.isdisjoint(final_test_c), "FATAL: Concept leakage between train and test set!"
    assert final_train_c.isdisjoint(final_val_c), "FATAL: Concept leakage between train and val set!"

    return train_df, val_df, test_df


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> Dict[str, Any]:
    """Computes comprehensive metrics table."""
    cm = confusion_matrix(y_true, y_pred).tolist()
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4) if len(np.unique(y_true)) > 1 else None,
        "confusion_matrix": cm,
    }


def main():
    print("=" * 65)
    print("Prerequisite Edge Classifier - Training & Validation")
    print("=" * 65)

    if not DATA_PATH.exists():
        print(f"Error: {DATA_PATH} not found. Run labeling script first.")
        sys.exit(1)

    print(f"\n[1/5] Loading labeled dataset from {DATA_PATH.name}...")
    df = pd.read_csv(DATA_PATH)
    print(f"      Total rows: {len(df):,}")
    print(f"      Label distribution: {df[TARGET_COLUMN].value_counts().to_dict()}")

    # 2. Concept-Aware Split
    print("\n[2/5] Partitioning train/val/test strictly BY CONCEPT (no leakage)...")
    train_df, val_df, test_df = concept_aware_split(df)

    print(f"      Train rows: {len(train_df):,} ({100*len(train_df)/len(df):.1f}%) | Pos: {train_df[TARGET_COLUMN].sum()}")
    print(f"      Val rows:   {len(val_df):,} ({100*len(val_df)/len(df):.1f}%) | Pos: {val_df[TARGET_COLUMN].sum()}")
    print(f"      Test rows:  {len(test_df):,} ({100*len(test_df)/len(df):.1f}%) | Pos: {test_df[TARGET_COLUMN].sum()}")
    print("      Verification: Zero concept overlap between splits [PASSED]")

    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df[TARGET_COLUMN].values

    X_val = val_df[FEATURE_COLUMNS].values
    y_val = val_df[TARGET_COLUMN].values

    X_test = test_df[FEATURE_COLUMNS].values
    y_test = test_df[TARGET_COLUMN].values

    # 3. Logistic Regression Baseline
    print("\n[3/5] Training Baseline: Logistic Regression...")
    baseline_clf = LogisticRegression(max_iter=1000, random_state=42)
    baseline_clf.fit(X_train, y_train)

    base_val_pred = baseline_clf.predict(X_val)
    base_val_prob = baseline_clf.predict_proba(X_val)[:, 1]
    base_metrics = evaluate_predictions(y_val, base_val_pred, base_val_prob)
    print(f"      Baseline Validation F1: {base_metrics['f1']:.4f} | Accuracy: {base_metrics['accuracy']:.4f}")

    # 4. XGBoost Primary Model + 5-Fold CV
    print("\n[4/5] Training Primary Model: XGBoost with 5-Fold Cross Validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1_scores = []
    
    for fold, (t_idx, v_idx) in enumerate(cv.split(X_train, y_train), 1):
        fold_model = XGBClassifier(
            n_estimators=150,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            random_state=42 + fold
        )
        fold_model.fit(X_train[t_idx], y_train[t_idx])
        pred_fold = fold_model.predict(X_train[v_idx])
        fold_f1 = f1_score(y_train[v_idx], pred_fold)
        cv_f1_scores.append(fold_f1)
        print(f"      Fold {fold} F1-Score: {fold_f1:.4f}")

    mean_cv_f1 = np.mean(cv_f1_scores)
    std_cv_f1 = np.std(cv_f1_scores)
    print(f"      Mean 5-Fold CV F1: {mean_cv_f1:.4f} (±{std_cv_f1:.4f})")

    # Train Final Primary XGBoost on full train set
    primary_clf = XGBClassifier(
        n_estimators=180,
        max_depth=4,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        eval_metric="logloss",
        random_state=42
    )
    primary_clf.fit(X_train, y_train)

    # 5. Full Evaluation on Val and Test
    print("\n[5/5] Evaluating Primary XGBoost on Validation & Test Sets...")
    val_pred = primary_clf.predict(X_val)
    val_prob = primary_clf.predict_proba(X_val)[:, 1]
    val_metrics = evaluate_predictions(y_val, val_pred, val_prob)

    test_pred = primary_clf.predict(X_test)
    test_prob = primary_clf.predict_proba(X_test)[:, 1]
    test_metrics = evaluate_predictions(y_test, test_pred, test_prob)

    print("\n" + "-" * 65)
    print(f"{'Metric':<20} | {'Validation':<15} | {'Test Set':<15}")
    print("-" * 65)
    for k in ["accuracy", "precision", "recall", "f1", "roc_auc"]:
        v_val = f"{val_metrics[k]:.4f}" if val_metrics[k] is not None else "N/A"
        t_val = f"{test_metrics[k]:.4f}" if test_metrics[k] is not None else "N/A"
        print(f"{k.capitalize():<20} | {v_val:<15} | {t_val:<15}")
    print("-" * 65)
    print(f"Confusion Matrix (Test Set): {test_metrics['confusion_matrix']}")

    # Sanity check against leakage (>97% alert)
    if test_metrics["accuracy"] > 0.97:
        print("  WARNING: Test accuracy > 97% - inspecting possible data leakage!")
    else:
        print("  Model performance verified on held-out test split.")

    # 6. Save Frozen Artifact and Report
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(primary_clf, ARTIFACT_PATH)
    print(f"\nSaved frozen model artifact -> {ARTIFACT_PATH}")

    full_report = {
        "model_type": "XGBClassifier",
        "features": FEATURE_COLUMNS,
        "n_train": len(train_df),
        "n_val": len(val_df),
        "n_test": len(test_df),
        "cv_5fold_mean_f1": round(float(mean_cv_f1), 4),
        "cv_5fold_std_f1": round(float(std_cv_f1), 4),
        "baseline_logistic_regression": base_metrics,
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)
    print(f"Saved full metrics report -> {METRICS_PATH}")
    print("=" * 65)


if __name__ == "__main__":
    main()

