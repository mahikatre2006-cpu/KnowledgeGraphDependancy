"""
threshold_analysis.py
=====================
Decision-Threshold Sensitivity Analysis for Cross-Domain Generalization.

Evaluates the frozen model artifact (app/ml/model_artifact.joblib) on the
non-IT held-out dataset (Cleaned_Files/cross_domain_test.csv or data/cross_domain_test.csv)
across a sweep of decision thresholds [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60].

Exports structured results to app/ml/cross_domain_threshold_report.json.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import pandas as pd
import joblib

from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    confusion_matrix,
)

project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Paths
MODEL_PATH = Path(project_root) / "app" / "ml" / "model_artifact.joblib"
DATA_PATH = Path(project_root) / "dependency" / "cross_domain_test.csv"
if not DATA_PATH.exists():
    DATA_PATH = Path(project_root) / "data" / "cross_domain_test.csv"
OUTPUT_REPORT_PATH = Path(project_root) / "app" / "ml" / "cross_domain_threshold_report.json"

FEATURE_COLUMNS = [
    "embedding_similarity",
    "order_delta",
    "domain_match",
    "keyword_overlap",
]
TARGET_COLUMN = "label"

THRESHOLDS = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]


def run_threshold_analysis() -> Dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model artifact not found at {MODEL_PATH}")
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Cross-domain test data not found at {DATA_PATH}")

    # 1. Load model and evaluation dataset
    model = joblib.load(MODEL_PATH)
    df = pd.read_csv(DATA_PATH)

    X = df[FEATURE_COLUMNS].values
    y = df[TARGET_COLUMN].values.astype(int)

    # 2. Predict continuous probabilities for class 1
    probabilities = model.predict_proba(X)[:, 1]

    n_total = len(df)
    n_pos = int(np.sum(y == 1))
    n_neg = int(np.sum(y == 0))

    threshold_results: List[Dict[str, Any]] = []

    print("=" * 80)
    print("Cross-Domain Decision-Threshold Sensitivity Analysis")
    print(f"Dataset: {DATA_PATH.name} (Total: {n_total}, Positives: {n_pos}, Negatives: {n_neg})")
    print("=" * 80)
    print(f"{'Threshold':<10} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Accuracy':<10} | Confusion Matrix [TN, FP, FN, TP]")
    print("-" * 80)

    for t in THRESHOLDS:
        preds = (probabilities >= t).astype(int)

        prec = float(precision_score(y, preds, zero_division=0))
        rec = float(recall_score(y, preds, zero_division=0))
        f1 = float(f1_score(y, preds, zero_division=0))
        acc = float(accuracy_score(y, preds))
        cm = confusion_matrix(y, preds)

        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        record = {
            "threshold": round(t, 2),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "accuracy": round(acc, 4),
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp,
            "confusion_matrix": [[tn, fp], [fn, tp]],
        }
        threshold_results.append(record)

        print(f"{t:<10.2f} | {prec:<10.4f} | {rec:<10.4f} | {f1:<10.4f} | {acc:<10.4f} | TN={tn:<3}, FP={fp:<2}, FN={fn:<2}, TP={tp:<2}")

    print("-" * 80)

    # Analyze whether any threshold raises recall while maintaining precision >= 0.80
    base_record = next(r for r in threshold_results if abs(r["threshold"] - 0.50) < 1e-4)
    base_recall = base_record["recall"]
    base_precision = base_record["precision"]

    qualifying_thresholds = [
        r for r in threshold_results
        if r["recall"] > base_recall and r["precision"] >= 0.80
    ]

    report_payload = {
        "dataset": DATA_PATH.name,
        "n_samples": n_total,
        "n_positives": n_pos,
        "n_negatives": n_neg,
        "baseline_threshold_0_50": base_record,
        "threshold_evaluations": threshold_results,
        "qualifying_thresholds_precision_ge_80_higher_recall": qualifying_thresholds,
    }

    OUTPUT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report_payload, f, indent=2)

    print(f"\nReport written to: {OUTPUT_REPORT_PATH}")
    if qualifying_thresholds:
        best_candidate = max(qualifying_thresholds, key=lambda x: (x["recall"], x["f1"]))
        print(f"Finding: Threshold {best_candidate['threshold']} raises recall from {base_recall:.4f} to {best_candidate['recall']:.4f} with precision {best_candidate['precision']:.4f} (>= 80%).")
    else:
        print("Finding: No threshold achieves higher recall than 0.50 while keeping precision >= 80%.")
    print("=" * 80)

    return report_payload


if __name__ == "__main__":
    run_threshold_analysis()

