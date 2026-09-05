"""
ai_label_suggestions.py
========================
Phase R1.2 - Local heuristic label suggestion using MiniLM embeddings.

Reads  : data/candidate_pairs.csv
Reads  : data/candidate_pairs.csv (or data/label_suggestions.csv if already generated)
Writes : data/label_suggestions.csv   (all pairs + suggested_label + reason)
         data/labeling_dataset.csv    (balanced >=3000-row subset, full feature schema)

No external API calls. Uses app/services/embedding_service.py (all-MiniLM-L6-v2).

Heuristic rules for label=1 (A is a prerequisite of B):
  Rule 1  - Lexical containment: concept_a is a substring of concept_b AND order_delta <= 10
  Rule 2  - High embedding similarity (>= 0.45) AND low order_delta (<= 5)
  Rule 3  - Foundational keyword in concept_a AND sim >= 0.25 AND order_delta <= 8
  Rule 4  - High embedding similarity (>= 0.60) AND order_delta <= 12
  Rule 5  - Same course, very close order (delta <= 2) AND sim >= 0.20
             (directly adjacent topics in same course are likely related prerequisites)
  Rule 6  - keyword_overlap >= 0.30 AND order_delta <= 6 (shared vocabulary + close)

Hard negatives (label=0 even if related):
  HN1    - embedding_similarity < 0.15  (no semantic relation)
  HN2    - order_delta >= 12 AND sim < 0.45 (far apart, weakly related)
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.embedding_service import LocalEmbeddingService

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATA_DIR = Path(project_root) / "data"
INPUT_CSV = DATA_DIR / "candidate_pairs.csv"
SUGGESTIONS_CSV = DATA_DIR / "label_suggestions.csv"
DATASET_CSV = DATA_DIR / "labeling_dataset.csv"

TARGET_TOTAL_ROWS = 5000          # final dataset size (well above >=3000 gate)
TARGET_POSITIVE_RATIO = 0.40      # ~40% label=1

FOUNDATIONAL_KEYWORDS = {
    "basic", "basics", "foundation", "foundations", "introduction", "intro",
    "fundamental", "fundamentals", "overview", "principle", "principles",
    "definition", "concept", "concepts", "history", "background",
    "architecture", "design", "model", "theory", "algorithm", "structure",
    "type", "types", "classification", "generation", "representation",
    "review", "summary", "survey",
}

NOISE_PATTERNS = [
    r"^\d{7}$",
    r"^\d{7}[#\*\s]?$",
    r"^21\d{5}",
    r"^[A-Z]{2}\d{3,4}$",
    r"^total$",
    r"^program elective",
    r"^multi$",
    r"^disciplinary",
    r"^common to",
    r"^to be taken",
    r"^by the university",
    r"^theory.*tutorial.*credit",
    r"^stream bucket",
    r"^indian knowledge system",
    r"^.{1,3}$",
    r"^\d+$",
    r"[#@\*]{2,}",
    r"^\d{3,}[#\*]",
]


def is_noise(text: str) -> bool:
    t = str(text).strip().lower()
    for pat in NOISE_PATTERNS:
        if re.search(pat, t):
            return True
    return False


def keyword_overlap_vec(a_series: pd.Series, b_series: pd.Series) -> pd.Series:
    """Vectorized Jaccard on word tokens."""
    results = []
    for a, b in zip(a_series, b_series):
        sa = set(re.findall(r"\w+", str(a).lower()))
        sb = set(re.findall(r"\w+", str(b).lower()))
        if not sa or not sb:
            results.append(0.0)
        else:
            results.append(len(sa & sb) / len(sa | sb))
    return pd.Series(results, index=a_series.index)


def has_foundational_kw(text: str) -> bool:
    words = set(re.findall(r"\w+", str(text).lower()))
    return bool(words & FOUNDATIONAL_KEYWORDS)


def assign_label(row) -> tuple:
    """
    Returns (label: int, reason: str)
    """
    ca = str(row["concept_a"]).lower().strip()
    cb = str(row["concept_b"]).lower().strip()
    sim = float(row["embedding_similarity"])
    delta = int(row["order_delta"])
    kw = float(row["keyword_overlap"])
    fk_a = bool(row["fk_a"])

    # Rule 1 - Lexical containment
    if ca in cb and delta <= 10:
        return 1, f"Lexical containment + delta={delta}"

    # Rule 4 - Very high sim alone
    if sim >= 0.60 and delta <= 12:
        return 1, f"High sim={sim:.3f} + delta={delta}"

    # Rule 2 - High sim + close order
    if sim >= 0.45 and delta <= 5:
        return 1, f"sim={sim:.3f}>=0.45 + delta={delta}<=5"

    # Rule 6 - Keyword overlap + proximity
    if kw >= 0.30 and delta <= 6:
        return 1, f"kw_overlap={kw:.3f}>=0.30 + delta={delta}<=6"

    # Rule 3 - Foundational keyword
    if fk_a and sim >= 0.25 and delta <= 8:
        return 1, f"Foundational kw in A + sim={sim:.3f} + delta={delta}"

    # Rule 5 - Same course adjacent topics
    if delta <= 2 and sim >= 0.20:
        return 1, f"Adjacent same-course topics: delta={delta} + sim={sim:.3f}"

    # Hard Negative 1
    if sim < 0.15:
        return 0, f"Low sim={sim:.3f} - no semantic relation"

    # Hard Negative 2
    if delta >= 12 and sim < 0.45:
        return 0, f"delta={delta}>=12 + sim={sim:.3f}<0.45 - far + weakly related"

    return 0, f"No prereq signal: sim={sim:.3f}, delta={delta}, kw={kw:.3f}"


def main():
    print("=" * 60)
    print("KDG Phase R1.2 - Local Heuristic Label Suggestions")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Load and clean candidate pairs
    # ------------------------------------------------------------------
    print("\n[1/5] Loading candidate_pairs.csv...")
    df = pd.read_csv(INPUT_CSV)
    total_raw = len(df)
    print(f"      Raw rows: {total_raw:,}")
    if SUGGESTIONS_CSV.exists() and SUGGESTIONS_CSV.stat().st_size > 1000:
        print(f"\n[Fast path] Found existing {SUGGESTIONS_CSV.name}, loading directly...")
        df = pd.read_csv(SUGGESTIONS_CSV)
        print(f"      Loaded {len(df):,} pairs from {SUGGESTIONS_CSV.name}")
    else:
        # 1. Load and clean candidate pairs
        print("\n[1/5] Loading candidate_pairs.csv...")
        df = pd.read_csv(INPUT_CSV)
        total_raw = len(df)
        print(f"      Raw rows: {total_raw:,}")

    df = df[~df["concept_a"].astype(str).apply(is_noise)]
    df = df[~df["concept_b"].astype(str).apply(is_noise)]
    df = df.reset_index(drop=True)
    print(f"      After noise filter: {len(df):,} rows ({total_raw - len(df):,} removed)")
        df = df[~df["concept_a"].astype(str).apply(is_noise)]
        df = df[~df["concept_b"].astype(str).apply(is_noise)]
        df = df.reset_index(drop=True)
        print(f"      After noise filter: {len(df):,} rows ({total_raw - len(df):,} removed)")

    df["order_delta"] = df["order_delta"].fillna(1).astype(int)
    df["domain_match"] = df["domain_match"].fillna(1).astype(int)
        df["order_delta"] = df["order_delta"].fillna(1).astype(int)
        df["domain_match"] = df["domain_match"].fillna(1).astype(int)

    # ------------------------------------------------------------------
    # 2. Encode unique concepts once
    # ------------------------------------------------------------------
    print("\n[2/5] Encoding unique concepts with all-MiniLM-L6-v2...")
    all_concepts = pd.concat([df["concept_a"], df["concept_b"]]).unique().tolist()
    print(f"      Unique concepts: {len(all_concepts):,}")
        # 2. Encode unique concepts once
        print("\n[2/5] Encoding unique concepts with all-MiniLM-L6-v2...")
        all_concepts = pd.concat([df["concept_a"], df["concept_b"]]).unique().tolist()
        print(f"      Unique concepts: {len(all_concepts):,}")

    raw_emb = LocalEmbeddingService.encode_batch(all_concepts)
    norms = np.linalg.norm(raw_emb, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10
    norm_emb = raw_emb / norms
    concept_to_idx = {c: i for i, c in enumerate(all_concepts)}
    print(f"      Embedding matrix: {norm_emb.shape}")
        raw_emb = LocalEmbeddingService.encode_batch(all_concepts)
        norms = np.linalg.norm(raw_emb, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        norm_emb = raw_emb / norms
        concept_to_idx = {c: i for i, c in enumerate(all_concepts)}
        print(f"      Embedding matrix: {norm_emb.shape}")

    # ------------------------------------------------------------------
    # 3. Compute features vectorized
    # ------------------------------------------------------------------
    print("\n[3/5] Computing embedding similarity and features...")
        # 3. Compute features vectorized
        print("\n[3/5] Computing embedding similarity and features...")
        idx_a = df["concept_a"].map(concept_to_idx).values
        idx_b = df["concept_b"].map(concept_to_idx).values

    idx_a = df["concept_a"].map(concept_to_idx).values
    idx_b = df["concept_b"].map(concept_to_idx).values
        chunk_size = 10000
        sims = np.empty(len(df), dtype=np.float32)
        for start in range(0, len(df), chunk_size):
            end = min(start + chunk_size, len(df))
            sims[start:end] = (norm_emb[idx_a[start:end]] * norm_emb[idx_b[start:end]]).sum(axis=1)

    # Vectorized cosine similarity: element-wise dot products of normalized rows
    # Process in chunks to avoid huge memory spike
    chunk_size = 10000
    sims = np.empty(len(df), dtype=np.float32)
    for start in range(0, len(df), chunk_size):
        end = min(start + chunk_size, len(df))
        sims[start:end] = (norm_emb[idx_a[start:end]] * norm_emb[idx_b[start:end]]).sum(axis=1)
        df["embedding_similarity"] = np.clip(sims, -1.0, 1.0).round(4)
        df["keyword_overlap"] = keyword_overlap_vec(df["concept_a"], df["concept_b"])
        df["fk_a"] = df["concept_a"].apply(has_foundational_kw)
        print(f"      Features computed for {len(df):,} pairs")

    df["embedding_similarity"] = np.clip(sims, -1.0, 1.0).round(4)
    df["keyword_overlap"] = keyword_overlap_vec(df["concept_a"], df["concept_b"])
    df["fk_a"] = df["concept_a"].apply(has_foundational_kw)
    print(f"      Features computed for {len(df):,} pairs")
        # 4. Apply heuristic labels
        print("\n[4/5] Applying heuristic rules...")
        results = df.apply(assign_label, axis=1)
        df["suggested_label"] = [r[0] for r in results]
        df["reason"] = [r[1] for r in results]

    # ------------------------------------------------------------------
    # 4. Apply heuristic labels
    # ------------------------------------------------------------------
    print("\n[4/5] Applying heuristic rules...")
    results = df.apply(assign_label, axis=1)
    df["suggested_label"] = [r[0] for r in results]
    df["reason"] = [r[1] for r in results]
        # Save full suggestions
        out_sug = df.drop(columns=["fk_a"]).rename(columns={"label": "original_label"})
        out_sug.to_csv(SUGGESTIONS_CSV, index=False)
        print(f"      Saved {len(out_sug):,} rows -> {SUGGESTIONS_CSV}")

    pos = df["suggested_label"].sum()
    pos = int(df["suggested_label"].sum())
    neg = len(df) - pos
    print(f"      label=1: {pos:,}  ({100*pos/len(df):.1f}%)")
    print(f"      label=0: {neg:,}  ({100*neg/len(df):.1f}%)")
    print(f"      Suggested label=1: {pos:,}  ({100*pos/len(df):.1f}%)")
    print(f"      Suggested label=0: {neg:,}  ({100*neg/len(df):.1f}%)")

    # Save full suggestions (drop helper col)
    out_sug = df.drop(columns=["fk_a"]).rename(columns={"label": "original_label"})
    out_sug.to_csv(SUGGESTIONS_CSV, index=False)
    print(f"      Saved {len(out_sug):,} rows -> {SUGGESTIONS_CSV}")

    # ------------------------------------------------------------------
    # 5. Sample balanced dataset
    # ------------------------------------------------------------------
    print(f"\n[5/5] Sampling balanced dataset (target {TARGET_TOTAL_ROWS:,} rows, ~{TARGET_POSITIVE_RATIO:.0%} positive)...")

    positives = df[df["suggested_label"] == 1]
    negatives = df[df["suggested_label"] == 0]

    n_pos = int(TARGET_TOTAL_ROWS * TARGET_POSITIVE_RATIO)
    n_neg = TARGET_TOTAL_ROWS - n_pos

    if len(positives) < n_pos:
        n_pos = len(positives)
        n_neg = min(len(negatives), max(n_pos * 2, TARGET_TOTAL_ROWS - n_pos))
        print(f"      NOTE: Only {n_pos:,} positives available - adjusting to {n_pos}+/{n_neg}-")

    sampled_pos = positives.sample(n=n_pos, random_state=42)
    sampled_neg = negatives.sample(n=min(n_neg, len(negatives)), random_state=42)

    dataset = pd.concat([sampled_pos, sampled_neg], ignore_index=True)
    dataset = dataset.sample(frac=1, random_state=42).reset_index(drop=True)

    # Clean columns to ensure single label column
    for col in ["label", "original_label"]:
        if col in dataset.columns:
            dataset = dataset.drop(columns=[col])
    dataset = dataset.rename(columns={"suggested_label": "label"})

    out_cols = [
        "concept_a", "concept_b", "Course_Code", "source_syllabus",
        "embedding_similarity", "order_delta", "domain_match", "keyword_overlap", "label"
    ]
    dataset = dataset[out_cols]
    dataset = dataset[out_cols].copy()

    # Cycle check: drop (A->B) + (B->A) both positive
    # Use .values to avoid duplicate-index issues after concat+reset
    dataset = dataset.reset_index(drop=True)
    pos_mask = dataset["label"].values == 1
    pos_set = set(zip(
        dataset.loc[pos_mask, "concept_a"].values,
        dataset.loc[pos_mask, "concept_b"].values,
        dataset[dataset["label"] == 1]["concept_a"].values,
        dataset[dataset["label"] == 1]["concept_b"].values
    ))

    def is_cycle(row):
        return row["label"] == 1 and (row["concept_b"], row["concept_a"]) in pos_set
    to_drop_idx = []
    seen = set()
    for idx, (a, b, lbl) in enumerate(zip(dataset["concept_a"], dataset["concept_b"], dataset["label"])):
        if lbl == 1:
            rev = (b, a)
            if rev in pos_set:
                if rev not in seen:
                    seen.add((a, b))
                    to_drop_idx.append(idx)

    cycle_mask = dataset.apply(is_cycle, axis=1)
    if cycle_mask.sum() > 0:
        print(f"      Removing {int(cycle_mask.sum())} cyclic positive pairs")
        dataset = dataset[~cycle_mask].reset_index(drop=True)
    if to_drop_idx:
        print(f"      Removing {len(to_drop_idx)} cyclic positive pairs")
        dataset = dataset.drop(index=to_drop_idx).reset_index(drop=True)

    dataset.to_csv(DATASET_CSV, index=False)

    final_pos = int(dataset["label"].sum())
    final_total = len(dataset)
    print(f"      Saved {final_total:,} rows -> {DATASET_CSV}")
    print(f"      label=1: {final_pos:,}  ({100*final_pos/final_total:.1f}%)")
    print(f"      label=0: {final_total - final_pos:,}  ({100*(final_total - final_pos)/final_total:.1f}%)")

    print("\n" + "=" * 60)
    print("R1 Gate Check:")
    gate_ok = final_total >= 3000 and 0.25 <= final_pos / final_total <= 0.75
    if gate_ok:
        print(f"  PASSED -- {final_total:,} rows, {100*final_pos/final_total:.1f}% positive")
        print("  labeling_dataset.csv is ready for Phase R2.")
    else:
        print(f"  FAILED -- {final_total:,} rows, {100*final_pos/final_total:.1f}% positive")
        print("  Minimum: >=3000 rows, 25-75% positive rate.")
    print("=" * 60)


if __name__ == "__main__":
    main()

