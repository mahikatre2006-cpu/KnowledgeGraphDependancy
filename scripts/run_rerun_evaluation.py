import os
import sys
import json
import re
import numpy as np
from pathlib import Path
import pandas as pd
import fitz

sys.stdout.reconfigure(encoding='utf-8')

REVIEW_DIR = Path("DATA/review")
CACHE_DIR = Path("DATA/processed/gemini_cache")

def normalize_text_for_match(text: str) -> str:
    if not text:
        return ""
    # 1. dehyphenate line-break hyphens: "inter-\nactive" -> "interactive"
    t = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    # 2. replace unicode dashes/quotes
    t = t.replace('\u2013', '-').replace('\u2014', '-').replace('\u2015', '-')
    t = t.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    # 3. collapse whitespace and newlines to a single space
    t = re.sub(r'\s+', ' ', t)
    # 4. strip and lowercase
    return t.strip().lower()

def word_in_quote(w: str, norm_quote: str) -> bool:
    if re.search(r'\b' + re.escape(w) + r'\b', norm_quote):
        return True
    # plural / singular
    if w.endswith('s') and len(w) > 3 and re.search(r'\b' + re.escape(w[:-1]) + r'\b', norm_quote):
        return True
    if w.endswith('es') and len(w) > 4 and re.search(r'\b' + re.escape(w[:-2]) + r'\b', norm_quote):
        return True
    # compound word (e.g. semigroups -> semi group)
    cw = re.sub(r'[^a-z0-9]', '', w)
    cq = re.sub(r'[^a-z0-9]', '', norm_quote)
    if cw in cq or (len(cw) > 3 and cw[:-1] in cq):
        return True
    return False

def validate_subject_topics(raw_topics: list, page_texts: dict):
    accepted = []
    rejected = []
    seen_names = set()
    quote_lengths = []
    
    normalized_pages = {p: normalize_text_for_match(text) for p, text in page_texts.items()}
    
    banned_words = [
        'mark', 'marks', 'credit', 'credits', 'hour', 'hours', 'textbook', 'text book',
        'reference', 'syllabus', 'course outcome', 'assessment', 'prerequisite',
        'co mapping', 'internal assessment', 'term work', 'duration'
    ]
    
    for t in raw_topics:
        # Rule 3: Topic names come directly from original text, un-normalized
        name = t.get("name", "").strip()
        unit = t.get("unit", "").strip()
        quote = t.get("source_quote", "").strip()
        page = t.get("page")
        
        words = name.split()
        norm_name = normalize_text_for_match(name)
        norm_quote = normalize_text_for_match(quote)
        
        quote_lengths.append(len(quote))
        
        # 1. Quote presence check
        if not quote:
            rejected.append((t, "empty_source_quote"))
            continue
            
        # Rule 2: Reject quotes over 200 characters
        if len(quote) > 200:
            rejected.append((t, f"quote_length_exceeds_200_chars ({len(quote)} chars)"))
            continue
            
        matched_page = None
        if page in normalized_pages and norm_quote in normalized_pages[page]:
            matched_page = page
        else:
            for p, p_text in normalized_pages.items():
                if norm_quote in p_text:
                    matched_page = p
                    break
                    
        if not matched_page:
            rejected.append((t, f"source_quote_not_found_on_page_{page}"))
            continue
            
        # Rule 2: Reject if fewer than 60% of topic words appear in quote
        topic_words = re.findall(r'\b[a-z0-9]+\b', norm_name)
        if topic_words:
            matched_words = [w for w in topic_words if word_in_quote(w, norm_quote)]
            pct = len(matched_words) / len(topic_words)
            if pct < 0.60:
                rejected.append((t, f"words_in_quote_below_60_percent ({len(matched_words)}/{len(topic_words)} = {pct*100:.1f}%)"))
                continue
                
        # Rule 1: Topic length: allow 1-word topics when standalone in quote. Max 8 words.
        if len(words) < 1 or len(words) > 8:
            rejected.append((t, f"word_count_out_of_bounds ({len(words)} words)"))
            continue
            
        # Duplicate check
        if norm_name in seen_names:
            rejected.append((t, f"duplicate_topic: '{name}'"))
            continue
            
        # Non-ASCII / garbage check: allow letters, numbers, spaces, and valid syllabus typography
        if not re.match(r'^[a-zA-Z0-9\s\-\/\(\)\.\,\&\+\#\:\'’‘“”–—]+$', name):
            rejected.append((t, f"non_ascii_or_special_chars: '{name}'"))
            continue
            
        # Banned words check
        has_banned = False
        for bw in banned_words:
            if re.search(r'\b' + re.escape(bw) + r'\b', norm_name):
                rejected.append((t, f"contains_banned_word: '{bw}'"))
                has_banned = True
                break
        if has_banned:
            continue
            
        seen_names.add(norm_name)
        accepted.append({
            "name": name,
            "unit": unit,
            "source_quote": quote,
            "page": matched_page
        })
        
    return accepted, rejected, quote_lengths

def run_evaluation():
    print("=" * 105)
    print("STAGE B PILOT EVALUATION (AFTER AMENDMENTS & 2113112 RE-RUN)")
    print("=" * 105)
    
    with open("DATA/processed/gemini_cache/2113112_rerun.json", "r", encoding="utf-8") as f:
        data_2113112 = json.load(f)
        
    pdf_2113112 = "DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf"
    doc_2113112 = fitz.open(pdf_2113112)
    pages_2113112 = {p: doc_2113112[p-1].get_text("text") for p in [19, 20, 21]}
    
    raw_topics_2113112 = data_2113112.get("topics", [])
    accepted_2113112, rejected_2113112, q_lens_2113112 = validate_subject_topics(raw_topics_2113112, pages_2113112)
    
    q_arr = np.array(q_lens_2113112)
    med_q = np.median(q_arr)
    p95_q = np.percentile(q_arr, 95)
    max_q = np.max(q_arr)
    
    print(f"\n>>> Pilot Subject: 2113112 - Discrete Structures and Graph Theory (NEP-2020, Sem III)")
    print(f"    Raw topics extracted:   {len(raw_topics_2113112)}")
    print(f"    Final accepted count:   {len(accepted_2113112)}")
    print(f"    Rejected topics:        {len(rejected_2113112)}")
    if rejected_2113112:
        for r_top, reason in rejected_2113112:
            print(f"      * Rejected '{r_top.get('name')}': {reason}")
    else:
        print("      * No topics rejected (0 rejections)")
        
    print(f"\n--- Quote Length Stats (Characters) ---")
    print(f"    Median quote length:    {med_q:.1f} chars")
    print(f"    P95 quote length:       {p95_q:.1f} chars")
    print(f"    Max quote length:       {max_q:.1f} chars  (Limit: <= 200 chars)")
    
    # Coverage check
    print(f"\n--- Coverage Check per Module ---")
    mod_counts = {
        "Module 0 (Prerequisite)": 0,
        "Module I (Crisp Set Theory and Logic)": 0,
        "Module II (Mathematical Relations)": 0,
        "Module III (Functions)": 0,
        "Module IV (Counting)": 0,
        "Module V (Algebraic Structures)": 0,
        "Module VI (Graph Theory)": 0,
    }
    
    for t in accepted_2113112:
        u = t["unit"].lower()
        if "prerequisite" in u or "module 0" in u:
            mod_counts["Module 0 (Prerequisite)"] += 1
        elif "module i:" in u or "crisp set" in u:
            mod_counts["Module I (Crisp Set Theory and Logic)"] += 1
        elif "module ii:" in u or "relations" in u:
            mod_counts["Module II (Mathematical Relations)"] += 1
        elif "module iii:" in u or "functions" in u:
            mod_counts["Module III (Functions)"] += 1
        elif "module iv:" in u or "counting" in u:
            mod_counts["Module IV (Counting)"] += 1
        elif "module v:" in u or "algebraic" in u:
            mod_counts["Module V (Algebraic Structures)"] += 1
        elif "module vi:" in u or "graph" in u:
            mod_counts["Module VI (Graph Theory)"] += 1
            
    for mod_name, count in mod_counts.items():
        print(f"    {mod_name:<42} : {count:>2} topics")
        
    # Check coverage warnings
    print(f"\n--- Coverage Warnings (< 3 topics) ---")
    raw_mod0 = (
        "Basic Set Theory, Logical Operators, Truth Tables, Cartesian product, Types of Functions. "
        "Basic Algebra and Number Theory, Fundamental Counting Principle, Permutations, Combinations. Graph Basics."
    )
    raw_mod3 = (
        "Functions: Types: Injective, Surjective, and Bijective Functions. Composition, Inverse Functions. Real life applications of Functions.\n"
        "Self-learning Topics: Practical applications of function in Neural Network, Determining risk factors for insurance rates, Taxes and tax brackets, Vending machines, etc."
    )
    
    for mod_name, count in mod_counts.items():
        if count < 3:
            print(f"    COVERAGE_WARNING: '{mod_name}' has {count} topics (< 3).")
            if "0" in mod_name:
                print(f"      [Raw lines]: {raw_mod0}\n")
            elif "III" in mod_name:
                print(f"      [Raw lines]: {raw_mod3}\n")
                
    print(f"--- Pilot Gate Summary ---")
    gate_ok = 8 <= len(accepted_2113112) <= 60
    print(f"    Quality Gate [8-60 topics]: {'PASS' if gate_ok else 'FAIL'} ({len(accepted_2113112)} topics)")
    print(f"    Requests used: 1 fresh API request (stored in cache)")
    
    # Update DATA/review/extraction_pilot.csv
    pilot_csv_path = REVIEW_DIR / "extraction_pilot.csv"
    existing_df = pd.read_csv(pilot_csv_path)
    
    # Retain ITC501 and CSC303
    retained_df = existing_df[existing_df["course_code"].astype(str) != "2113112"]
    
    new_rows = []
    for t in accepted_2113112:
        new_rows.append({
            "course_code": "2113112",
            "title": "Discrete Structures and Graph Theory",
            "semester": "III",
            "unit": t["unit"],
            "topic_name": t["name"],
            "source_quote": t["source_quote"],
            "page": t["page"],
            "human_ok": ""
        })
    new_df = pd.DataFrame(new_rows)
    updated_pilot_df = pd.concat([retained_df, new_df], ignore_index=True)
    # Ensure human_ok column is strictly empty string
    updated_pilot_df["human_ok"] = ""
    updated_pilot_df.to_csv(pilot_csv_path, index=False)
    
    print(f"\n    Updated '{pilot_csv_path}' successfully (Total rows: {len(updated_pilot_df)})")
    print(f"    - ITC501 rows: {len(updated_pilot_df[updated_pilot_df['course_code'] == 'ITC501'])}")
    print(f"    - CSC303 rows: {len(updated_pilot_df[updated_pilot_df['course_code'] == 'CSC303'])}")
    print(f"    - 2113112 rows: {len(updated_pilot_df[updated_pilot_df['course_code'] == '2113112'])}")
    print(f"    - human_ok is completely blank across all rows: {bool((updated_pilot_df['human_ok'] == '').all())}")

def update_budget():
    print("\n" + "=" * 105)
    print("5. UPDATED API BUDGET (96 EXTRACTABLE SUBJECTS)")
    print("Added: ITDO7012 (Optimization Techniques) and ITDO8013 (Simulation and Modeling)")
    print("=" * 105)
    
    n_subj = 96
    extract_calls = n_subj + 10  # 96 subjects + 10 reruns (~10% gate failures)
    label_calls = n_subj * 2     # 96 subjects x 2 runs (within-subject only)
    single_run_edges = n_subj * 25 # ~25 edges per subject = 2,400 edges
    union_edges = int(1.4 * single_run_edges) # 1.4 x 2,400 = 3,360 edges
    verifier_calls = (union_edges + 39) // 40 # 3,360 / 40 = 84 calls
    baseline_calls = (300 + 49) // 50         # 300 gold pairs / 50 = 6 calls
    total_calls = extract_calls + label_calls + verifier_calls + baseline_calls
    
    print(f"1. Extraction (96 subjects + 10 reruns):               {extract_calls:>5} calls")
    print(f"2. Within-subject Labeling (96 subjects x 2 runs):     {label_calls:>5} calls")
    print(f"   - Single-run positive edges estimate:               {single_run_edges:>5} edges (~25 positive edges/subject)")
    print(f"   - Union of run1 and run2 edges (1.4x estimate):     {union_edges:>5} edges")
    print(f"3. Verifier calls (union / 40 edges per call):         {verifier_calls:>5} calls  (3,360 / 40)")
    print(f"4. Gemini-direct baseline (300 gold pairs / 50):       {baseline_calls:>5} calls")
    print("-" * 60)
    print(f"TOTAL RECOMPUTED API BUDGET (96 SUBJECTS):             {total_calls:>5} calls")

if __name__ == "__main__":
    run_evaluation()
    update_budget()

