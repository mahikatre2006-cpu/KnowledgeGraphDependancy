from fastapi import APIRouter, HTTPException, status
import json
from pathlib import Path

router = APIRouter(prefix="/metrics", tags=["Model Evaluation Metrics"])

METRICS_FILE = Path(__file__).resolve().parent.parent / "ml" / "metrics_report.json"


@router.get("", summary="Get Prerequisite Classifier Evaluation Metrics", status_code=status.HTTP_200_OK)
def get_model_metrics():
    """
    Returns the evaluation metrics report for the prerequisite edge classifier:
    - 5-Fold Stratified Cross Validation Mean & Std F1
    - Baseline Logistic Regression metrics
    - Validation set metrics
    - Held-out Test set metrics (Accuracy, Precision, Recall, F1, ROC-AUC, Confusion Matrix)
    - Cross-Domain generalization metrics (Mechanical, Civil, Electrical)
    """
    if not METRICS_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Metrics report not found. Please run model training first."
        )

    try:
        with open(METRICS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read metrics report: {str(e)}"
        )
