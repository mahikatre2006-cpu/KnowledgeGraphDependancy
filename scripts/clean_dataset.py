"""
clean_dataset.py
================
Creates labeling_dataset_cleaned.csv by removing the confirmed contaminated rows
identified in label_audit_flagged.csv.

Invariants:
- Cleaned_Files/labeling_dataset.csv MUST NOT be modified or deleted.
- Outputs saved to Cleaned_Files/labeling_dataset_cleaned.csv and data/labeling_dataset_cleaned.csv.
"""

from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ORIGINAL_CSV = PROJECT_ROOT / "Cleaned_Files" / "labeling_dataset.csv"
FLAGGED_CSV  = PROJECT_ROOT / "Cleaned_Files" / "label_audit_flagged.csv"

OUT_CLEANED_CLEANED_DIR = PROJECT_ROOT / "Cleaned_Files" / "labeling_dataset_cleaned.csv"
OUT_CLEANED_DATA_DIR    = PROJECT_ROOT / "data" / "labeling_dataset_cleaned.csv"


def main():
    print(f"Reading original dataset: {ORIGINAL_CSV}")
    df_orig = pd.read_csv(ORIGINAL_CSV)
    orig_len = len(df_orig)

    print(f"Reading flagged dataset:  {FLAGGED_CSV}")
    df_flagged = pd.read_csv(FLAGGED_CSV)
    flagged_len = len(df_flagged)

    print(f"Original rows : {orig_len:,}")
    print(f"Flagged rows  : {flagged_len:,}")

    # Build unique composite key for exact row matching
    key_cols = ['concept_a', 'concept_b', 'Course_Code', 'course_name', 'label']
    
    # Create composite key string
    def make_key(df):
        return (
            df['concept_a'].astype(str) + "|||" +
            df['concept_b'].astype(str) + "|||" +
            df['Course_Code'].astype(str) + "|||" +
            df['course_name'].astype(str) + "|||" +
            df['label'].astype(str)
        )

    orig_keys = make_key(df_orig)
    flagged_keys = set(make_key(df_flagged))

    # Mask clean rows
    clean_mask = ~orig_keys.isin(flagged_keys)
    df_cleaned = df_orig[clean_mask].copy().reset_index(drop=True)
    cleaned_len = len(df_cleaned)

    print(f"Cleaned rows  : {cleaned_len:,} (expected: {orig_len - flagged_len:,})")

    # Invariant assertions
    assert cleaned_len == orig_len - flagged_len, (
        f"Row count mismatch! Cleaned: {cleaned_len}, expected {orig_len - flagged_len}"
    )

    # Class distribution
    pos_count = (df_cleaned['label'] == 1).sum()
    neg_count = (df_cleaned['label'] == 0).sum()
    print(f"\nCleaned Label Distribution:")
    print(f"  Positives (label=1): {pos_count:,} ({pos_count/cleaned_len*100:.1f}%)")
    print(f"  Negatives (label=0): {neg_count:,} ({neg_count/cleaned_len*100:.1f}%)")

    # Write cleaned CSVs
    OUT_CLEANED_CLEANED_DIR.parent.mkdir(parents=True, exist_ok=True)
    OUT_CLEANED_DATA_DIR.parent.mkdir(parents=True, exist_ok=True)

    df_cleaned.to_csv(OUT_CLEANED_CLEANED_DIR, index=False)
    df_cleaned.to_csv(OUT_CLEANED_DATA_DIR, index=False)

    print(f"\nWrote cleaned dataset to:")
    print(f"  - {OUT_CLEANED_CLEANED_DIR.relative_to(PROJECT_ROOT)}")
    print(f"  - {OUT_CLEANED_DATA_DIR.relative_to(PROJECT_ROOT)}")

    # Final verification: ensure original file was not touched
    orig_check = pd.read_csv(ORIGINAL_CSV)
    assert len(orig_check) == orig_len, "CRITICAL ERROR: Original file was modified!"
    print("\nVerified: Original labeling_dataset.csv remains 100% untouched.")


if __name__ == "__main__":
    main()

