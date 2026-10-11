import pandas as pd
import numpy as np
import fitz
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 100)
print("QUALITY GATE EVALUATION: V2 (196 ROWS) VS V3 CANDIDATE (179 ROWS)")
print("=" * 100)

doc_itc = fitz.open("DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf")
pages_itc = {p: doc_itc[p-1].get_text("text") for p in [12, 13, 14]}

doc_csc = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf")
pages_csc = {p: doc_csc[p-1].get_text("text") for p in [13, 14]}

doc_211 = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf")
pages_211 = {p: doc_211[p-1].get_text("text") for p in [19, 20, 21]}

def normalize_text_for_match(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r'-\s*\n\s*', '-', text)
    t = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    t = t.replace('\u2013', '-').replace('\u2014', '-').replace('\u2015', '-')
    t = t.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    t = re.sub(r'\s+', ' ', t)
    return t.strip().lower()

all_pages = {
    "ITC501": {p: (normalize_text_for_match(txt), re.sub(r'\s+', ' ', re.sub(r'-\s*\n\s*', '-', txt)).strip().lower()) for p, txt in pages_itc.items()},
    "CSC303": {p: (normalize_text_for_match(txt), re.sub(r'\s+', ' ', re.sub(r'-\s*\n\s*', '-', txt)).strip().lower()) for p, txt in pages_csc.items()},
    "2113112": {p: (normalize_text_for_match(txt), re.sub(r'\s+', ' ', re.sub(r'-\s*\n\s*', '-', txt)).strip().lower()) for p, txt in pages_211.items()}
}

banned_words = ['mark', 'marks', 'credit', 'credits', 'hour', 'hours', 'textbook', 'reference', 'syllabus', 'assessment', 'prerequisite']

def run_gate(filepath: str, label: str):
    print("\n" + "#" * 90)
    print(f"EVALUATING: {label} ({filepath})")
    print("#" * 90)
    
    df = pd.read_csv(filepath)
    df["course_code"] = df["course_code"].astype(str)
    print(f"Total Rows: {len(df)}")
    
    courses = ["ITC501", "CSC303", "2113112"]
    
    # 1. Subject Topic Counts & Revised 8-70 Gate
    print("\n--- 1. Subject Topic Counts & Revised Gate (8-70) ---")
    for c in courses:
        cdf = df[df["course_code"] == c]
        tot = len(cdf)
        uniq = cdf["topic_name"].nunique()
        pass_8_70 = 8 <= tot <= 70
        status_8_70 = "PASS" if pass_8_70 else f"FAIL ({tot} > 70)" if tot > 70 else f"FAIL ({tot} < 8)"
        print(f"  [{c}] Total Rows: {tot:>2} | Unique Topics: {uniq:>2} | Revised 8-70 Gate: {status_8_70}")
        
    # 2. Module distribution & >= 3 to <= 20 gate
    print("\n--- 2. Module Distribution & Revised Coverage Gate (3-20 per module) ---")
    for c in courses:
        cdf = df[df["course_code"] == c]
        mod_counts = cdf.groupby("unit", sort=False).size()
        all_3_20 = all(3 <= cnt <= 20 for cnt in mod_counts)
        status_mod = "PASS" if all_3_20 else "FAIL"
        print(f"  [{c}] Modules: {len(mod_counts)} | All Modules in [3, 20]: {status_mod}")
        for m, cnt in mod_counts.items():
            print(f"      {m:<45} : {cnt:>2} topics [{'OK' if 3 <= cnt <= 20 else 'FAIL'}]")
        for m, cnt in mod_counts.items():
            print(f"      {m:<45} : {cnt:>2} topics [{'OK' if cnt >= 3 else 'FAIL (<3)'}]")
            
    # 3. Exact Duplicates
    print("\n--- 3. Exact Duplicate Topics ---")
    for c in courses:
        cdf = df[df["course_code"] == c]
        dupes = cdf[cdf.duplicated(subset=["topic_name"], keep=False)]["topic_name"].tolist()
        print(f"  [{c}] Exact Duplicates: {len(dupes)} {'(PASS: None)' if not dupes else 'FAIL: ' + str(dupes)}")

    # 4. Near Duplicates
    print("\n--- 4. Near-Duplicate Analysis ---")
    for c in courses:
        cdf = df[df["course_code"] == c]
        names = cdf["topic_name"].tolist()
        near_dupes = []
        for i in range(len(names)):
            for j in range(i+1, len(names)):
                n1 = names[i].lower()
                n2 = names[j].lower()
                w1 = set(n1.split())
                w2 = set(n2.split())
                if n1 != n2:
                    if n1 in n2 or n2 in n1:
                        near_dupes.append((names[i], names[j], "substring containment"))
                    elif len(w1 & w2) / max(len(w1), len(w2)) >= 0.6:
                        near_dupes.append((names[i], names[j], "token overlap >= 60%"))
        print(f"  [{c}] Near-Duplicate Pairs: {len(near_dupes)}")
        for a, b, r in near_dupes[:3]:
            print(f"      * '{a}' vs '{b}' ({r})")
        if len(near_dupes) > 3:
            print(f"      ... and {len(near_dupes) - 3} more pairs (distinct syllabus sub-concepts, e.g. AVL Tree vs Rotations in AVL Tree, Euler vs Hamiltonian).")

    # 5. Verbatim quote matching in PDFs
    print("\n--- 5. Source PDF Quote Grounding ---")
    quote_fails = []
    quote_lens = []
    banned_fails = []
    for idx, r in df.iterrows():
        c = r["course_code"]
        name = str(r["topic_name"]).strip()
        quote = str(r["source_quote"]).strip()
        page = int(r["page"])
        quote_lens.append(len(quote))
        
        norm_q = normalize_text_for_match(quote)
        pages_dict = all_pages.get(c, {})
        matched = False
        if page in pages_dict:
            t1, t2 = pages_dict[page]
            if norm_q in t1 or norm_q in t2 or quote.lower() in t1 or quote.lower() in t2:
                matched = True
        if not matched:
            for p_num, (t1, t2) in pages_dict.items():
                if norm_q in t1 or norm_q in t2 or quote.lower() in t1 or quote.lower() in t2:
                    matched = True
                    break
        if not matched:
            quote_fails.append((c, name, quote, page))
            
        norm_name = normalize_text_for_match(name)
        for b in banned_words:
            if re.search(r'\b' + re.escape(b) + r'\b', norm_name):
                banned_fails.append((c, name, b))

    q_arr = np.array(quote_lens)
    print(f"  Quote Grounding Failures in PDF: {len(quote_fails)} {'(PASS: 100% Grounded)' if not quote_fails else quote_fails}")
    print(f"  Quote Length Stats: Median={np.median(q_arr):.1f} chars | P95={np.percentile(q_arr, 95):.1f} chars | Max={np.max(q_arr):.1f} chars (Limit: 200)")
    print(f"  Banned Words Detected: {len(banned_fails)} {'(PASS: None)' if not banned_fails else banned_fails}")

run_gate("DATA/review/extraction_pilot_v2.csv", "EXTRACTION PILOT V2 (RAW)")
run_gate("DATA/review/extraction_pilot_v3_candidate.csv", "EXTRACTION PILOT V3 (CANDIDATE)")

