"""
evaluate_cross_domain.py
========================
Cross-Domain Generalization Evaluator

Loads the trained model artifact (app/ml/model_artifact.joblib) and evaluates
it on the independent non-IT engineering dataset (Cleaned_Files/cross_domain_test.csv).

Measures out-of-domain transfer performance on Mechanical, Civil, and Electrical subjects.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd
import joblib

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

TEST_DATA_PATH = Path(project_root) / "dependency" / "cross_domain_test.csv"
if not TEST_DATA_PATH.exists():
    TEST_DATA_PATH = Path(project_root) / "data" / "cross_domain_test.csv"
MODEL_PATH = Path(project_root) / "app" / "ml" / "model_artifact.joblib"
METRICS_PATH = Path(project_root) / "app" / "ml" / "metrics_report.json"

FEATURE_COLUMNS = [
    "embedding_similarity",
    "order_delta",
    "domain_match",
    "keyword_overlap",
]
TARGET_COLUMN = "label"


def main():
    print("=" * 65)
    print("Cross-Domain Generalization Evaluation")
    print("=" * 65)

    if not MODEL_PATH.exists():
        print(f"Error: Frozen model artifact not found at {MODEL_PATH}.")
        print("Please run app/ml/train_classifier.py first.")
        sys.exit(1)

    if not TEST_DATA_PATH.exists():
        print(f"Error: Cross-domain test data not found at {TEST_DATA_PATH}.")
        sys.exit(1)

    print(f"\n[1/3] Loading frozen model artifact from {MODEL_PATH.name}...")
    model = joblib.load(MODEL_PATH)

    print(f"\n[2/3] Loading non-IT evaluation dataset ({TEST_DATA_PATH.name})...")
    df = pd.read_csv(TEST_DATA_PATH)
    print(f"      Total rows: {len(df):,}")
    print(f"      Subjects included: {df['Course_Code'].unique().tolist()}")
    print(f"      Label distribution: {df[TARGET_COLUMN].value_counts().to_dict()}")

    X = df[FEATURE_COLUMNS].values
    y = df[TARGET_COLUMN].values

    print("\n[3/3] Running inference and computing evaluation metrics...")
    y_pred = model.predict(X)
    y_prob = model.predict_proba(X)[:, 1]

    acc = accuracy_score(y, y_pred)
    prec = precision_score(y, y_pred, zero_division=0)
    rec = recall_score(y, y_pred, zero_division=0)
    f1 = f1_score(y, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y, y_prob) if len(np.unique(y)) > 1 else None
    cm = confusion_matrix(y, y_pred).tolist()

    print("\n" + "-" * 65)
    print(f"{'Metric':<25} | {'Cross-Domain (Non-IT)':<20}")
    print("-" * 65)
    print(f"{'Accuracy':<25} | {acc:.4f}")
    print(f"{'Precision':<25} | {prec:.4f}")
    print(f"{'Recall':<25} | {rec:.4f}")
    print(f"{'F1-Score':<25} | {f1:.4f}")
    print(f"{'ROC-AUC':<25} | {roc_auc:.4f}" if roc_auc else f"{'ROC-AUC':<25} | N/A")
    print("-" * 65)
    print(f"Confusion Matrix: {cm}")

    # Append cross_domain_metrics to metrics_report.json
    if METRICS_PATH.exists():
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            report = json.load(f)
        report["cross_domain_metrics"] = {
            "n_samples": len(df),
            "subjects": df["Course_Code"].unique().tolist(),
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1": round(float(f1), 4),
            "roc_auc": round(float(roc_auc), 4) if roc_auc else None,
            "confusion_matrix": cm,
        }
        with open(METRICS_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nUpdated {METRICS_PATH.name} with cross-domain validation figures.")
    print("=" * 65)


if __name__ == "__main__":
    main()

