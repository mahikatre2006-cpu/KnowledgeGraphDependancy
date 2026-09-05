"""
full_pipeline.py
================
End-to-end pipeline: PDF extraction -> candidate pairs -> labels -> XGBoost training

Handles:
  - MU NEP-2020 combined Sem III+IV PDFs (module-table format with DETAILED SYLLABUS)
  - SEM-V monolithic PDFs (Unit I/II/III header format)

Output: Cleaned_Files/ directory
  - candidate_pairs.csv
  - label_suggestions.csv
  - labeling_dataset.csv
  - app/ml/model_artifact.joblib
  - app/ml/metrics_report.json
"""

import re
import sys
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any

import fitz  # PyMuPDF
import numpy as np
import pandas as pd
import joblib

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix,
)
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier

project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.embedding_service import LocalEmbeddingService

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR = Path(project_root) / "DATA"
OUT_DIR = Path(project_root) / "Cleaned_Files"
OUT_DIR.mkdir(exist_ok=True)

CANDIDATE_CSV = OUT_DIR / "candidate_pairs.csv"
SUGGESTIONS_CSV = OUT_DIR / "label_suggestions.csv"
DATASET_CSV = OUT_DIR / "labeling_dataset.csv"
MODEL_DIR = Path(project_root) / "app" / "ml"
MODEL_DIR.mkdir(exist_ok=True)
ARTIFACT_PATH = MODEL_DIR / "model_artifact.joblib"
METRICS_PATH = MODEL_DIR / "metrics_report.json"

WINDOW = 15          # max positional gap for candidate pairs
TARGET_ROWS = 5000
TARGET_POS_RATIO = 0.40

# Admin/elective course codes to skip (no real topic content)
SKIP_CODE_RE = re.compile(r'^(2993|2994|2995|2996|2997|2998|2999)\d+$')

# ─────────────────────────────────────────────────────────────────────────────
# Topic Cleaning & Noise Filtering
# ─────────────────────────────────────────────────────────────────────────────

_NOISE_PATS = [
    re.compile(r'^\d{7}$'),
    re.compile(r'^[A-Z]{2,4}\d{3,4}$'),
    re.compile(r'^\d+$'),
    re.compile(r'^[-\u2013\u2014\s]+$'),
    re.compile(r'^(total|na|nil|n\.a\.|--|---)$', re.I),
    re.compile(r'^(unit|module|chapter|section|sr\.?\s*no\.?)$', re.I),
    re.compile(r'^(theory|practical|tutorial|credits?|marks?|hours?|hrs?)$', re.I),
    re.compile(r'^co\s*mapping', re.I),
    re.compile(r'^co\s*\d', re.I),
    re.compile(r'^\w{1,3}$'),                         # 1-3 char tokens
    re.compile(r'^\d{1,2}\s*[-\.]\s*$'),
    re.compile(r'^(https?|www\.)', re.I),
    re.compile(r'https?://', re.I),                   # any URL-containing line
    re.compile(r'^(reference|textbook|online|books?):?$', re.I),
    re.compile(r'^(iat|iat-i|iat-ii|end\s*sem|test\s*\d)$', re.I),
    re.compile(r'^prerequisite[s:]?$', re.I),
    re.compile(r'^rationale:?$', re.I),
    re.compile(r'^course\s*(objective|outcome|code|name|description)s?:?$', re.I),
    re.compile(r'^\s*(and|or|the|to|of|in|for|a|an)\s*$', re.I),
    re.compile(r'^self[\s-]learning\s*topics?:?\s*$', re.I),  # bare self-learning line
    re.compile(r'^assessment:?$', re.I),
    re.compile(r'^(lab|mini\s*project|open\s*elective)', re.I),
    re.compile(r'^below\s+[\d.]+', re.I),            # grading rubric rows
    re.compile(r'iat-i\s*\+\s*iat', re.I),           # exam table bleed-in
    re.compile(r'^course\s*code\s*course\s*name', re.I),  # table header bleed-in
    re.compile(r'end\s*sem\s*exam', re.I),            # exam scheme header
    re.compile(r'teaching\s*scheme\s*\(contact\s*hours\)', re.I),
    re.compile(r'^\(average\)$', re.I),
    re.compile(r'^(explore|topics|concepts|overview|details)$', re.I),
    re.compile(r'^self-learning$', re.I),
    re.compile(r'^only\s+up\s+to', re.I),            # math denominator noise
    re.compile(r'^\(without\s*proof\)$', re.I),
]


def is_noise(text: str) -> bool:
    t = text.strip()
    if not t or len(t) < 5 or len(t) > 150:
        return True
    if re.fullmatch(r'[\d\s\-\u2013\u2014\.\,\(\)\*\+\/]+', t):
        return True
    # Must have at least 2 meaningful words
    words = re.findall(r'[A-Za-z]{3,}', t)
    if len(words) < 2:
        return True
    for pat in _NOISE_PATS:
        if pat.search(t):
            return True
    return False


def clean_topic(text: str) -> str:
    t = text.strip()
    # Strip leading numbering: "1.", "I.", "a)", "(2)", "•", "-"
    t = re.sub(r'^[\d]+[\.\)]\s*', '', t)
    t = re.sub(r'^[ivxlcdmIVXLCDM]+[\.\)]\s*', '', t)
    t = re.sub(r'^[•\-–—\*►▶◆]\s*', '', t)
    # Strip trailing hours/marks e.g. "(5 hrs)", "[CO1]", "CO1,CO2"
    t = re.sub(r'\s*\[\s*CO\s*\d[\d,\s]*\]', '', t, flags=re.I)
    t = re.sub(r'\s*(CO\s*\d[\d,\s]*)+$', '', t, flags=re.I)
    t = re.sub(r'\s*\(\s*\d+\s*(hrs?|hours?|marks?|credits?)\s*\)\s*$', '', t, flags=re.I)
    t = re.sub(r'\s+\d+\s*$', '', t)
    return t.strip(' ,.;:-')


# ─────────────────────────────────────────────────────────────────────────────
# Core Extraction
# ─────────────────────────────────────────────────────────────────────────────

DETAIL_HDR_RE = re.compile(
    r'DETAILED\s+SYLLABUS|Detailed\s+Contents?|Detailed\s+Content',
    re.IGNORECASE
)
COURSE_CODE_RE = re.compile(r'\b(\d{7})\b')

# Module row: Roman numeral or digit 0-9, then a module name (4-70 chars)
MODULE_NUM_RE = re.compile(r'^([IVXLCDM]{1,5}|0|[1-9]\d?)\s{1,12}(.{4,70})$')


def extract_topics_from_page_text(page_text: str) -> List[str]:
    """
    Extracts topics from a DETAILED SYLLABUS page.

    MU NEP-2020 PDF tables are rendered by PyMuPDF with interleaved column lines:
      'I '          <- lone roman numeral (Sr.No column)
      'Linear '     <- module name line 1 (Name of Module column)
      'Algebra '    <- module name line 2
      '(Theory..' <- module name line 3
      '1. Topic..' <- detail content line
      '2. Topic..' <- detail content line

    Strategy: state machine — detect roman numeral alone, accumulate name lines,
    then accumulate detail content lines as topics.
    """
    topics = []

    det_match = DETAIL_HDR_RE.search(page_text)
    if not det_match:
        return topics

    content = page_text[det_match.end():]
    lines = [l.strip() for l in content.split('\n') if l.strip()]

    LONE_NUM_RE = re.compile(r'^([IVXLCDM]{1,5}|0|[1-9]\d?)$')
    SKIP_HDR_RE = re.compile(
        r'^(Sr\.?\s*No\.?|Name\s*of\s*Module|Detailed\s*Content|Hours|CO\s*Mapping|LO\b)',
        re.I
    )
    STOP_RE = re.compile(r'^(Books?|References?|Online\s*Ref|Assessment|Term\s*Work)', re.I)

    state = "idle"          # idle | collecting_name | collecting_detail
    name_parts: List[str] = []
    current_module: str = ""

    def flush_name():
        nonlocal current_module
        if name_parts:
            raw = ' '.join(name_parts)
            cleaned = clean_topic(raw)
            if not is_noise(cleaned) and not re.match(r'^prerequisite', cleaned, re.I):
                current_module = cleaned
                topics.append(current_module)
            name_parts.clear()

    for line in lines:
        if STOP_RE.match(line):
            flush_name()
            break

        if SKIP_HDR_RE.match(line):
            continue

        # Lone number/roman numeral -> start of new module row
        if LONE_NUM_RE.match(line):
            flush_name()
            state = "collecting_name"
            name_parts.clear()
            continue

        if state == "collecting_name":
            # If line looks like a detail content line (starts with digit+period or is long),
            # module name is complete -> switch to collecting_detail
            is_detail_line = (
                re.match(r'^\d+\.\s+\S', line) or
                re.match(r'^Self-learning', line, re.I) or
                (len(line) > 60 and ',' in line)
            )
            if is_detail_line:
                flush_name()
                state = "collecting_detail"
                # Also extract this line as a topic
                if ',' in line and len(line) < 300:
                    for part in line.split(','):
                        c = clean_topic(part)
                        if not is_noise(c) and len(c) > 5:
                            topics.append(c)
                else:
                    c = clean_topic(line)
                    if not is_noise(c) and len(c) > 5:
                        topics.append(c)
            elif re.fullmatch(r'[\d\s\-\u2013\u2014.,]+', line):
                # Pure number line = hours/marks column -> skip, name is done
                flush_name()
                state = "collecting_detail"
            elif line.upper() in ('CO1', 'CO2', 'CO3', 'CO4', 'CO5', 'CO6', 'CO7'):
                flush_name()
                state = "collecting_detail"
            else:
                # Continuation of module name
                name_parts.append(line)

        elif state == "collecting_detail":
            # Check if this is a new module starting (lone roman numeral handled above)
            # Extract content topics
            if re.match(r'^Self-learning', line, re.I):
                continue
            if re.fullmatch(r'[\d\s\-\u2013\u2014.,\(\)CO]+', line):
                continue
            if not re.search(r'[A-Za-z]{4}', line):
                continue
            if ',' in line and len(line) < 300:
                for part in line.split(','):
                    c = clean_topic(part)
                    if not is_noise(c) and len(c) > 5:
                        topics.append(c)
            else:
                c = clean_topic(line)
                if not is_noise(c) and len(c) > 5:
                    topics.append(c)

    flush_name()
    return topics


def extract_topics_unit_headers(full_text: str) -> List[str]:
    """
    Extracts topics from Unit I / Unit II header style (SEM-V PDFs).
    """
    topics = []
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
    UNIT_RE = re.compile(
        r'^(?:unit|module|chapter|part|section)\s*[-:]?\s*([0-9ivxlcdm]+)\s*[-:]?\s*(.*)$',
        re.IGNORECASE
    )
    in_unit = False
    for line in lines:
        if UNIT_RE.match(line):
            in_unit = True
            continue
        if in_unit:
            if re.match(r'^(references?|textbooks?|books?)\s*[:\-]', line, re.I):
                break
            for part in re.split(r'[;•\*]|\b-\b', line):
                cleaned = clean_topic(part)
                if not is_noise(cleaned):
                    topics.append(cleaned)
    return topics


def extract_course_blocks_from_pdf(pdf_path: Path) -> List[Tuple[str, str, List[str]]]:
    """
    Returns list of (course_code, course_name, [topic strings]) for every
    subject found in the PDF.

    Detection logic:
    - A "subject header page" has exactly 2 occurrences of the same 7-digit code
      AND contains 'Teaching Scheme' or 'Credits Assigned' (the per-subject header table).
    - DETAILED SYLLABUS content follows immediately on the next 1-4 pages.
    """
    doc = fitz.open(str(pdf_path))
    pages_text = [doc[i].get_text('text') for i in range(len(doc))]

    # Step 1: Identify subject header pages
    subject_pages: List[Tuple[int, str, str]] = []  # (page_idx, code, name)
    TEACHING_SCHEME_RE = re.compile(r'Teaching\s*Scheme|Credits\s*Assigned|Examination\s*[Ss]cheme', re.I)

    for i, text in enumerate(pages_text):
        codes = COURSE_CODE_RE.findall(text)
        if not codes:
            continue

        unique_codes = list(dict.fromkeys(codes))  # preserve order, dedup

        # Subject header page: has 1-2 unique codes, and looks like a credit/scheme table
        if len(unique_codes) <= 2 and TEACHING_SCHEME_RE.search(text):
            code = unique_codes[0]
            if SKIP_CODE_RE.match(code):
                continue

            # Extract course name: look for meaningful text near the code
            name = ""
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            code_seen = False
            for line in lines:
                if code in line:
                    code_seen = True
                    continue
                if code_seen and len(line) > 5 and len(line) < 100:
                    if not re.fullmatch(r'[\d\s\-–—\.\,]+', line):
                        if not re.match(r'^(course\s*code|theory|practical|tutorial|teaching|credits|exam|test|iat)', line, re.I):
                            name = line
                            break

            subject_pages.append((i, code, name or f"Subject_{code}"))

    # Deduplicate: keep first header page per code
    seen_codes: Dict[str, bool] = {}
    unique_subjects = []
    for page_idx, code, name in subject_pages:
        if code not in seen_codes:
            seen_codes[code] = True
            unique_subjects.append((page_idx, code, name))

    # Step 2: For each subject, collect DETAILED SYLLABUS content from subsequent pages
    results = []
    for k, (header_pg, code, name) in enumerate(unique_subjects):
        # Search range: from header page to the next subject's header page (max 10 pages)
        next_header_pg = unique_subjects[k + 1][0] if k + 1 < len(unique_subjects) else len(pages_text)
        search_end = min(header_pg + 10, next_header_pg, len(pages_text))
        next_pg = unique_subjects[k + 1][0] if k + 1 < len(unique_subjects) else len(pages_text)
        search_end = min(header_pg + 12, next_pg, len(pages_text))

        topics: List[str] = []

        for p_idx in range(header_pg, search_end):
            ptext = pages_text[p_idx]

            # Strategy A: Page has DETAILED SYLLABUS header — anchor extraction
            det_match = DETAIL_HDR_RE.search(ptext)
            if det_match:
                page_topics = extract_topics_from_page_text(ptext)
                topics.extend(page_topics)
                continue

            # Strategy B: Content-only page (no 7-digit code, just module table rows)
            has_code = bool(COURSE_CODE_RE.search(ptext))
            if not has_code:
                lines = [l.strip() for l in ptext.split('\n') if l.strip()]
                in_content = False
                for line in lines:
                    if re.match(r'^(Books?|References?|Online\s*Ref|Assessment|Term\s*Work)', line, re.I):
                        break
                    # Module row: roman numeral or number + module name
                    mod_m = re.match(r'^([IVXLCDM]{1,5}|0|[1-9]\d?)\s{1,12}(.{4,70})$', line)
                    if mod_m:
                        cand = clean_topic(mod_m.group(2))
                        if not is_noise(cand) and not re.match(r'^prerequisite', cand, re.I):
                            topics.append(cand)
                            in_content = True
                        continue
                    # Sub-topic content
                    if in_content and len(line) > 8 and re.search(r'[A-Za-z]{4}', line):
                        if re.fullmatch(r'[\d\s\-\u2013\u2014\.,\(\)]+', line):
                            continue
                        if ',' in line and len(line) < 300:
                            for part in line.split(','):
                                c = clean_topic(part)
                                if not is_noise(c) and len(c) > 5:
                                    topics.append(c)
                        else:
                            c = clean_topic(line)
                            if not is_noise(c) and len(c) > 5:
                                topics.append(c)

        # Fallback C: unit-header style (SEM-V format)
        if len(topics) < 3:
            block_text = '\n'.join(pages_text[header_pg:search_end])
            topics = extract_topics_unit_headers(block_text)

        # Deduplicate preserving order
        seen_t: set = set()
        deduped: List[str] = []
        for t in topics:
            key = re.sub(r'\s+', ' ', t.lower().strip())
            if key not in seen_t and not is_noise(t):
                seen_t.add(key)
                deduped.append(t)

        if len(deduped) >= 3:
            results.append((code, name, deduped))
            print(f"    [{code}] {name[:55]:<55}: {len(deduped)} topics")
        else:
            print(f"    [{code}] {name[:55]:<55}: SKIPPED ({len(deduped)} topics)")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2: Candidate Pair Generation
# ─────────────────────────────────────────────────────────────────────────────

def build_candidate_pairs(
    all_courses: List[Tuple[str, str, str, List[str]]]
) -> pd.DataFrame:
    rows = []
    for pdf_name, code, course_name, topics in all_courses:
        n = len(topics)
        for i in range(n):
            for j in range(i + 1, min(i + WINDOW, n)):
                rows.append({
                    "concept_a": topics[i],
                    "concept_b": topics[j],
                    "source_syllabus": pdf_name,
                    "Course_Code": code,
                    "course_name": course_name,
                    "order_delta": j - i,
                    "domain_match": 1,
                    "label": "",
                })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3: Embeddings + Heuristic Labels
# ─────────────────────────────────────────────────────────────────────────────

FOUNDATIONAL_KWS = {
    "basic", "basics", "foundation", "foundations", "introduction", "intro",
    "fundamental", "fundamentals", "overview", "principle", "principles",
    "definition", "concept", "concepts", "history", "background",
    "architecture", "design", "model", "theory", "algorithm", "structure",
    "type", "types", "classification", "generation", "representation",
}


def keyword_overlap(a: str, b: str) -> float:
    sa = set(re.findall(r'\w+', a.lower()))
    sb = set(re.findall(r'\w+', b.lower()))
    if not sa or not sb:
        return 0.0
    return round(len(sa & sb) / len(sa | sb), 4)


def heuristic_label(ca: str, cb: str, sim: float, delta: int, kw: float) -> Tuple[int, str]:
    a_low = ca.lower().strip()
    b_low = cb.lower().strip()
    fk_a = bool(set(re.findall(r'\w+', a_low)) & FOUNDATIONAL_KWS)

    if a_low in b_low and delta <= 10:
        return 1, f"Lexical containment + delta={delta}"
    if sim >= 0.60 and delta <= 12:
        return 1, f"High sim={sim:.3f} + delta={delta}"
    if sim >= 0.45 and delta <= 5:
        return 1, f"sim={sim:.3f}>=0.45 + delta={delta}<=5"
    if kw >= 0.30 and delta <= 6:
        return 1, f"kw_overlap={kw:.3f} + delta={delta}<=6"
    if fk_a and sim >= 0.25 and delta <= 8:
        return 1, f"Foundational kw + sim={sim:.3f} + delta={delta}"
    if delta <= 2 and sim >= 0.20:
        return 1, f"Adjacent topics: delta={delta} + sim={sim:.3f}"
    if sim < 0.15:
        return 0, f"Low sim={sim:.3f}"
    if delta >= 12 and sim < 0.45:
        return 0, f"Far apart: delta={delta} + sim={sim:.3f}"
    return 0, f"No signal: sim={sim:.3f} delta={delta} kw={kw:.3f}"


def compute_labels(df: pd.DataFrame) -> pd.DataFrame:
    all_concepts = list(set(df["concept_a"].tolist() + df["concept_b"].tolist()))
    print(f"  Encoding {len(all_concepts):,} unique concepts...")

    raw_emb = LocalEmbeddingService.encode_batch(all_concepts)
    norms = np.linalg.norm(raw_emb, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10
    norm_emb = raw_emb / norms
    c2idx = {c: i for i, c in enumerate(all_concepts)}
    print(f"  Embedding matrix: {norm_emb.shape}")

    idx_a = df["concept_a"].map(c2idx).values
    idx_b = df["concept_b"].map(c2idx).values
    chunk = 10000
    sims = np.empty(len(df), dtype=np.float32)
    for s in range(0, len(df), chunk):
        e = min(s + chunk, len(df))
        sims[s:e] = (norm_emb[idx_a[s:e]] * norm_emb[idx_b[s:e]]).sum(axis=1)

    df = df.copy().reset_index(drop=True)
    df["embedding_similarity"] = np.clip(sims, -1.0, 1.0).round(4)
    df["keyword_overlap"] = [
        keyword_overlap(str(r["concept_a"]), str(r["concept_b"]))
        for _, r in df.iterrows()
    ]

    labels, reasons = [], []
    for _, row in df.iterrows():
        lbl, rsn = heuristic_label(
            str(row["concept_a"]), str(row["concept_b"]),
            float(row["embedding_similarity"]),
            int(row["order_delta"]),
            float(row["keyword_overlap"])
        )
        labels.append(lbl)
        reasons.append(rsn)

    df["suggested_label"] = labels
    df["reason"] = reasons
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4: Train XGBoost
# ─────────────────────────────────────────────────────────────────────────────

FEATURE_COLS = ["embedding_similarity", "order_delta", "domain_match", "keyword_overlap"]
TARGET_COL = "label"


def concept_aware_split(df: pd.DataFrame, random_state: int = 42):
    courses = df["Course_Code"].drop_duplicates().sample(frac=1, random_state=random_state).tolist()
    total = len(df)
    train_target = int(total * 0.70)
    val_target = int(total * 0.15)

    train_courses, val_courses, test_courses = [], [], []
    cur_train, cur_val = 0, 0

    for c in courses:
        n = len(df[df["Course_Code"] == c])
        if cur_train + n <= train_target or not train_courses:
            train_courses.append(c)
            cur_train += n
        elif cur_val + n <= val_target or not val_courses:
            val_courses.append(c)
            cur_val += n
        else:
            test_courses.append(c)

    train_df = df[df["Course_Code"].isin(train_courses)].reset_index(drop=True)
    val_df = df[df["Course_Code"].isin(val_courses)].reset_index(drop=True)
    test_df = df[df["Course_Code"].isin(test_courses)].reset_index(drop=True)

    # Remove concept leakage
    train_c = set(train_df["concept_a"]) | set(train_df["concept_b"])
    val_df = val_df[~val_df["concept_a"].isin(train_c) & ~val_df["concept_b"].isin(train_c)].reset_index(drop=True)
    test_df = test_df[~test_df["concept_a"].isin(train_c) & ~test_df["concept_b"].isin(train_c)].reset_index(drop=True)

    # Assert disjoint
    tc = set(train_df["concept_a"]) | set(train_df["concept_b"])
    vc = set(val_df["concept_a"]) | set(val_df["concept_b"])
    ec = set(test_df["concept_a"]) | set(test_df["concept_b"])
    assert tc.isdisjoint(vc), "LEAK: Train-Val concept overlap!"
    assert tc.isdisjoint(ec), "LEAK: Train-Test concept overlap!"
    return train_df, val_df, test_df


def compute_metrics(y_true, y_pred, y_prob) -> Dict[str, Any]:
    return {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4) if len(np.unique(y_true)) > 1 else None,
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def train_and_evaluate(dataset: pd.DataFrame):
    print("\n  Splitting dataset concept-aware (70/15/15)...")
    train_df, val_df, test_df = concept_aware_split(dataset)
    print(f"  Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")
    print(f"  Train pos: {int(train_df[TARGET_COL].sum())} | Val pos: {int(val_df[TARGET_COL].sum())} | Test pos: {int(test_df[TARGET_COL].sum())}")
    print("  Zero concept overlap between splits [VERIFIED]")

    X_tr = train_df[FEATURE_COLS].values.astype(float)
    y_tr = train_df[TARGET_COL].values.astype(int)
    X_v = val_df[FEATURE_COLS].values.astype(float)
    y_v = val_df[TARGET_COL].values.astype(int)
    X_te = test_df[FEATURE_COLS].values.astype(float)
    y_te = test_df[TARGET_COL].values.astype(int)

    # Logistic Regression baseline
    print("\n  Logistic Regression baseline...")
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_tr, y_tr)
    lr_m = compute_metrics(y_v, lr.predict(X_v), lr.predict_proba(X_v)[:, 1])
    print(f"  Baseline Val F1: {lr_m['f1']:.4f} | Acc: {lr_m['accuracy']:.4f}")

    # XGBoost + 5-Fold CV
    print("\n  XGBoost + 5-Fold Stratified CV...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_f1s = []
    for fold, (ti, vi) in enumerate(skf.split(X_tr, y_tr), 1):
        m = XGBClassifier(
            n_estimators=150, max_depth=4, learning_rate=0.08,
            subsample=0.85, colsample_bytree=0.85,
            eval_metric='logloss', random_state=42 + fold, verbosity=0
        )
        m.fit(X_tr[ti], y_tr[ti])
        f = f1_score(y_tr[vi], m.predict(X_tr[vi]))
        cv_f1s.append(f)
        print(f"    Fold {fold} F1: {f:.4f}")

    mean_cv = float(np.mean(cv_f1s))
    std_cv = float(np.std(cv_f1s))
    print(f"  Mean 5-Fold CV F1: {mean_cv:.4f} (+/-{std_cv:.4f})")

    # Final model
    clf = XGBClassifier(
        n_estimators=180, max_depth=4, learning_rate=0.08,
        subsample=0.85, colsample_bytree=0.85,
        eval_metric='logloss', random_state=42, verbosity=0
    )
    clf.fit(X_tr, y_tr)

    val_m = compute_metrics(y_v, clf.predict(X_v), clf.predict_proba(X_v)[:, 1])
    test_m = compute_metrics(y_te, clf.predict(X_te), clf.predict_proba(X_te)[:, 1])

    print("\n" + "=" * 65)
    print(f"  {'Metric':<22} | {'Validation':<14} | Test Set")
    print("  " + "-" * 61)
    for k in ["accuracy", "precision", "recall", "f1", "roc_auc"]:
        vv = f"{val_m[k]:.4f}" if val_m[k] is not None else "N/A"
        tv = f"{test_m[k]:.4f}" if test_m[k] is not None else "N/A"
        print(f"  {k.capitalize():<22} | {vv:<14} | {tv}")
    print("  " + "-" * 61)
    print(f"  Confusion Matrix (Test) : {test_m['confusion_matrix']}")
    print("=" * 65)

    if test_m["accuracy"] and test_m["accuracy"] > 0.97:
        print("  WARNING: >97% accuracy - check for concept leakage!")

    joblib.dump(clf, ARTIFACT_PATH)
    print(f"\n  Model artifact saved -> {ARTIFACT_PATH}")

    report = {
        "model_type": "XGBClassifier",
        "features": FEATURE_COLS,
        "n_train": len(train_df), "n_val": len(val_df), "n_test": len(test_df),
        "cv_5fold_mean_f1": round(mean_cv, 4),
        "cv_5fold_std_f1": round(std_cv, 4),
        "baseline_logistic_regression": lr_m,
        "validation_metrics": val_m,
        "test_metrics": test_m,
    }
    METRICS_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"  Metrics report saved   -> {METRICS_PATH}")
    return clf


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("Syllabus Prerequisite Extraction & Training Pipeline")
    print("=" * 65)

    # Step 1 — Extract topic blocks
    print(f"\n[STEP 1] Extracting topics from all PDFs in {DATA_DIR} ...")
    all_courses: List[Tuple[str, str, str, List[str]]] = []
    pdf_files = sorted(DATA_DIR.glob("*.pdf"))
    print(f"  PDFs found: {[p.name for p in pdf_files]}\n")

    for pdf_path in pdf_files:
        print(f"  Processing: {pdf_path.name}")
        blocks = extract_course_blocks_from_pdf(pdf_path)
        for code, name, topics in blocks:
            all_courses.append((pdf_path.name, code, name, topics))

    total_topics = sum(len(c[3]) for c in all_courses)
    print(f"\n  Subjects extracted: {len(all_courses)} | Total topics: {total_topics}")

    if not all_courses:
        print("ERROR: No topics extracted. PDF structure not recognized.")
        sys.exit(1)

    # Step 2 — Candidate pairs
    print(f"\n[STEP 2] Building candidate topic pairs (window={WINDOW}) ...")
    pairs_df = build_candidate_pairs(all_courses)
    pairs_df.to_csv(CANDIDATE_CSV, index=False)
    print(f"  Candidate pairs: {len(pairs_df):,} -> {CANDIDATE_CSV.name}")

    # Step 3 — Embeddings + heuristic labels
    print(f"\n[STEP 3] Computing embeddings + heuristic labels ...")
    labeled_df = compute_labels(pairs_df)
    labeled_df.to_csv(SUGGESTIONS_CSV, index=False)
    pos = int(labeled_df["suggested_label"].sum())
    neg = len(labeled_df) - pos
    print(f"  Suggestions: {len(labeled_df):,} | label=1: {pos} ({100*pos/len(labeled_df):.1f}%) | label=0: {neg}")

    # Step 4 — Sample balanced dataset
    print(f"\n[STEP 4] Sampling balanced training dataset ...")
    positives = labeled_df[labeled_df["suggested_label"] == 1]
    negatives = labeled_df[labeled_df["suggested_label"] == 0]

    n_pos = int(TARGET_ROWS * TARGET_POS_RATIO)
    n_neg = TARGET_ROWS - n_pos

    if len(positives) < n_pos:
        n_pos = len(positives)
        n_neg = min(len(negatives), max(int(n_pos * 1.5), 1000))
        print(f"  NOTE: Only {n_pos} positives available. Using {n_pos}+ / {n_neg}-")

    sampled_pos = positives.sample(n=n_pos, random_state=42)
    sampled_neg = negatives.sample(n=min(n_neg, len(negatives)), random_state=42)

    dataset = pd.concat([sampled_pos, sampled_neg], ignore_index=True)
    dataset = dataset.sample(frac=1, random_state=42).reset_index(drop=True)
    if "label" in dataset.columns:
        dataset = dataset.drop(columns=["label"])
    dataset = dataset.rename(columns={"suggested_label": "label"})

    want_cols = ["concept_a", "concept_b", "Course_Code", "course_name", "source_syllabus",
                 "embedding_similarity", "order_delta", "domain_match", "keyword_overlap", "label"]
    dataset = dataset[[c for c in want_cols if c in dataset.columns]].copy().reset_index(drop=True)

    # Remove cyclic positive pairs using numpy — avoid pandas duplicate-index issue
    pos_mask = dataset["label"].values == 1
    pos_a = dataset["concept_a"].values[pos_mask]
    pos_b = dataset["concept_b"].values[pos_mask]
    label_arr = np.asarray(dataset["label"]).ravel()
    pos_mask = (label_arr == 1)
    pos_a = np.asarray(dataset["concept_a"])[pos_mask]
    pos_b = np.asarray(dataset["concept_b"])[pos_mask]
    pos_set = set(zip(pos_a, pos_b))

    drop_indices = []
    for idx in range(len(dataset)):
        if dataset.at[idx, "label"] == 1:
            rev = (dataset.at[idx, "concept_b"], dataset.at[idx, "concept_a"])
            if rev in pos_set:
                drop_indices.append(idx)

    if drop_indices:
        print(f"  Removing {len(drop_indices)} cyclic positive pairs")
        dataset = dataset.drop(index=drop_indices).reset_index(drop=True)

    dataset.to_csv(DATASET_CSV, index=False)
    final_pos = int(dataset["label"].sum())
    final_total = len(dataset)
    print(f"  Final dataset: {final_total:,} rows | label=1: {final_pos} ({100*final_pos/final_total:.1f}%) | label=0: {final_total - final_pos}")

    gate_ok = final_total >= 3000 and 0.25 <= final_pos / final_total <= 0.75
    print(f"  Dataset Size & Balance Requirement (>=3,000 rows): {'PASSED' if gate_ok else 'FAILED (insufficient data)'}")

    if final_total < 50:
        print("ERROR: Too few samples to train. Add more PDFs to DATA/ and re-run.")
        sys.exit(1)

    # Step 5 — Train
    print(f"\n[STEP 5] Training XGBoost prerequisite classifier ...")
    train_and_evaluate(dataset)

    print("\n" + "=" * 65)
    print("PIPELINE COMPLETE")
    print(f"  {CANDIDATE_CSV.name}  -> {CANDIDATE_CSV}")
    print(f"  {SUGGESTIONS_CSV.name} -> {SUGGESTIONS_CSV}")
    print(f"  {DATASET_CSV.name} -> {DATASET_CSV}")
    print(f"  model_artifact.joblib  -> {ARTIFACT_PATH}")
    print(f"  metrics_report.json    -> {METRICS_PATH}")
    print("=" * 65)


if __name__ == "__main__":
    main()
