"""
ingest_new_pdfs.py
==================
Classify PDFs in DATA/, run extraction, write candidate pair files.

Outputs (in data/):
  - new_candidate_pairs.csv        (it_training + diversity_training pairs, no label)
  - new_cross_domain_candidates.csv (reserved_test_only pairs, no label)
  - review_sample.csv              (120 stratified rows, empty your_label column)

Does NOT modify labeling_dataset.csv or cross_domain_test.csv.
"""

import sys
import random
import re
from pathlib import Path

import pandas as pd

# ── project root on sys.path ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.full_pipeline import extract_course_blocks_from_pdf, build_candidate_pairs

# ── paths ─────────────────────────────────────────────────────────────────────
DATA_DIR  = PROJECT_ROOT / "DATA"
OUT_DIR   = PROJECT_ROOT / "data"
OUT_DIR.mkdir(exist_ok=True)

NEW_PAIRS_CSV       = OUT_DIR / "new_candidate_pairs.csv"
NEW_CROSS_CSV       = OUT_DIR / "new_cross_domain_candidates.csv"
REVIEW_SAMPLE_CSV   = OUT_DIR / "review_sample.csv"

REVIEW_PER_BUCKET   = 60   # 60 it_training + 60 diversity_training = 120 total
RANDOM_SEED         = 42

# ── bucket classification ─────────────────────────────────────────────────────
# Each entry: (filename_substring_lower, bucket)
_CLASSIFICATION: dict[str, str] = {
    "6.9n-aiml.pdf":                                             "it_training",
    "6.14n-cse-aiml.pdf":                                        "it_training",
    "6.19-n-extc.pdf":                                           "it_training",
    "6.20n-b.e.-ai-ds.-sem-iii-iv.pdf":                         "it_training",
    "6.21-n-b.e.-ai-ml-sem-iii-iv.pdf":                         "it_training",
    "6.24-n-b.e.-computer-engineering-sem-iii-iv.pdf":           "it_training",
    "6.28n-ds.pdf":                                              "it_training",
    "6.34-n-b.e.-information-technology-sem-iii-iv.pdf":         "it_training",
    "6.39-n-b.e.-data-science-sem-iii-iv.pdf":                  "it_training",
    "6.41n-a-i-ai-ds-sem-iii-iv.pdf":                           "it_training",
    "6.54-n-b.e-computer-science-engineeringsem-iii-iv.pdf":     "it_training",
    "02 syllabus.pdf":                                           "it_training",
    "sem-v.pdf":                                                 "it_training",
    "syllabus-c prog.pdf":                                       "it_training",
    "professional_comm._ethics_theory_sem_i 2024-25.pdf":        "it_training",
    "applied chemistry syllabus 2024-25.pdf":                    "diversity_training",
    "new em syllabus 2024-25.pdf":                               "diversity_training",
    "6.40-n-chemical-engineering-sem-iii-iv.pdf":                "diversity_training",
    "6.23-n-b.e.-civil-engineeing-sem-iii-iv.pdf":              "reserved_test_only",
    "6.23-nb.e.-mechanical-engineering-sem-i-ii-2.pdf":         "reserved_test_only",
    "6.29-n-b.e.-electrical-engineering-sem-iii-iv.pdf":        "reserved_test_only",
    "6.35-n-b.e.-mechanical-engineeringsem-iii-iv.pdf":         "reserved_test_only",
    "6.44-n-b.e.-mecanical-automation-engineering-sem-iii-iv.pdf": "reserved_test_only",
    "6.51n-b.e.-electrical-computer-engineeringsem-iii-iv.pdf":  "reserved_test_only",
}


def classify_pdf(filename: str) -> str:
    key = filename.lower()
    if key in _CLASSIFICATION:
        return _CLASSIFICATION[key]
    # fallback: unknown
    return "UNKNOWN"


def main() -> None:
    random.seed(RANDOM_SEED)

    pdfs = sorted(DATA_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {DATA_DIR}")
        sys.exit(1)

    # Bucket -> list of (pdf_name, code, course_name, topics)
    it_courses:      list = []
    div_courses:     list = []
    test_courses:    list = []
    summary_rows:    list = []

    print("\n=== PDF Classification & Extraction ===\n")

    for pdf_path in pdfs:
        bucket = classify_pdf(pdf_path.name)
        print(f"  [{bucket:>20}]  {pdf_path.name}")

        if bucket == "UNKNOWN":
            print(f"    SKIPPED — unclassified filename")
            summary_rows.append({"filename": pdf_path.name, "bucket": "UNKNOWN", "topics_extracted": 0})
            continue

        courses = extract_course_blocks_from_pdf(pdf_path)
        topic_total = sum(len(t) for _, _, t in courses)
        summary_rows.append({
            "filename":        pdf_path.name,
            "bucket":          bucket,
            "topics_extracted": topic_total,
        })

        # Attach pdf_name so build_candidate_pairs can use it as source_syllabus
        tagged = [(pdf_path.name, code, name, topics) for code, name, topics in courses]

        if bucket == "it_training":
            it_courses.extend(tagged)
        elif bucket == "diversity_training":
            div_courses.extend(tagged)
        elif bucket == "reserved_test_only":
            test_courses.extend(tagged)

    # ── print summary table ───────────────────────────────────────────────────
    print("\n=== Summary ===")
    print(f"{'Filename':<58} {'Bucket':<22} {'Topics':>6}")
    print("-" * 90)
    for row in summary_rows:
        print(f"{row['filename']:<58} {row['bucket']:<22} {row['topics_extracted']:>6}")

    # ── build candidate pairs ─────────────────────────────────────────────────
    training_courses = it_courses + div_courses

    df_train = build_candidate_pairs(training_courses) if training_courses else pd.DataFrame()
    df_test  = build_candidate_pairs(test_courses)     if test_courses     else pd.DataFrame()

    # ── tag bucket column; ensure label stays empty ───────────────────────────
    if not df_train.empty:
        df_train["bucket"] = df_train["source_syllabus"].apply(
            lambda s: "it_training" if classify_pdf(s) == "it_training" else "diversity_training"
        )
        df_train["label"] = ""

    if not df_test.empty:
        df_test["label"] = ""

    # ── write output CSVs ─────────────────────────────────────────────────────
    df_train.to_csv(NEW_PAIRS_CSV, index=False)
    df_test.to_csv(NEW_CROSS_CSV, index=False)
    print(f"\nWrote {len(df_train):,} rows  ->  {NEW_PAIRS_CSV.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {len(df_test):,} rows  ->  {NEW_CROSS_CSV.relative_to(PROJECT_ROOT)}")

    # ── build review_sample.csv (stratified 60+60) ───────────────────────────
    sample_rows: list = []

    if not df_train.empty:
        for bucket_name in ("it_training", "diversity_training"):
            bucket_df = df_train[df_train["bucket"] == bucket_name]
            n = min(REVIEW_PER_BUCKET, len(bucket_df))
            sampled = bucket_df.sample(n=n, random_state=RANDOM_SEED)
            sample_rows.append(sampled)
            print(f"  Sample: {n} rows from {bucket_name}")

    if sample_rows:
        review_df = pd.concat(sample_rows, ignore_index=True)
    else:
        review_df = pd.DataFrame()

    # Add empty your_label column; drop label column so reviewer uses your_label
    if not review_df.empty:
        review_df = review_df.drop(columns=["label"], errors="ignore")
        review_df["your_label"] = ""
        review_df = review_df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    review_df.to_csv(REVIEW_SAMPLE_CSV, index=False)
    print(f"Wrote {len(review_df):,} rows  ->  {REVIEW_SAMPLE_CSV.relative_to(PROJECT_ROOT)}")

    # ── sanity check: no label values written ─────────────────────────────────
    assert df_train.empty or (df_train["label"] == "").all(), "BUG: label column is not empty in new_candidate_pairs.csv"
    assert df_test.empty  or (df_test["label"]  == "").all(), "BUG: label column is not empty in new_cross_domain_candidates.csv"
    assert review_df.empty or (review_df["your_label"] == "").all(), "BUG: your_label column is not empty in review_sample.csv"

    print("\nAll label columns confirmed empty.")


if __name__ == "__main__":
    main()

