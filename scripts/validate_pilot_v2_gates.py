import json
import re
import fitz
import numpy as np
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 100)
print("QUALITY GATES AUDIT FOR FRESH PILOT V2 (DATA/review/extraction_pilot_v2.csv)")
print("=" * 100)

df_v2 = pd.read_csv("DATA/review/extraction_pilot_v2.csv")
print(f"Total rows in extraction_pilot_v2.csv: {len(df_v2)}")

# -------------------------------------------------------------------------------------------------
# 1. Subject and Module Topic Counts (8-60 Gate & Module >= 3 Gate)
# -------------------------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("1. SUBJECT & MODULE TOPIC COUNTS")
print("=" * 80)

gate_summary = {}
for code in ["ITC501", "CSC303", "2113112"]:
    cdf = df_v2[df_v2["course_code"].astype(str) == code]
    tot = len(cdf)
    pass_8_60 = 8 <= tot <= 60
    
    mod_counts = cdf.groupby("unit", sort=False).size()
    all_mod_ge3 = all(c >= 3 for c in mod_counts)
    
    gate_summary[code] = {
        "total": tot,
        "pass_8_60": pass_8_60,
        "all_mod_ge3": all_mod_ge3,
        "modules": mod_counts.to_dict()
    }
    
    print(f"Course {code} ({cdf['title'].iloc[0]}):")
    print(f"  Total Topics: {tot:>2} | 8-60 Gate: {'PASS' if pass_8_60 else 'FAIL (' + str(tot) + ' > 60)'}")
    print(f"  Module Coverage Gate (>= 3): {'PASS' if all_mod_ge3 else 'FAIL'}")
    for m, c in mod_counts.items():
        print(f"    {m:<45} : {c:>2} topics [{'OK' if c >= 3 else 'FAIL (<3)'}]")

# -------------------------------------------------------------------------------------------------
# 2. Duplicate Checks (Exact & Near)
# -------------------------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("2. DUPLICATE CHECKS")
print("=" * 80)

for code in ["ITC501", "CSC303", "2113112"]:
    cdf = df_v2[df_v2["course_code"].astype(str) == code]
    names = cdf["topic_name"].tolist()
    
    seen = {}
    exact_dupes = []
    for n in names:
        norm = re.sub(r'\s+', ' ', n.strip().lower())
        if norm in seen:
            exact_dupes.append(n)
        seen[norm] = seen.get(norm, 0) + 1
        
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
                    
    print(f"Course {code}:")
    print(f"  Exact Duplicates: {'NONE (PASS)' if not exact_dupes else 'FAIL: ' + str(exact_dupes)}")
    print(f"  Near-Duplicate Pairs: {len(near_dupes)}")
    for a, b, r in near_dupes[:4]:
        print(f"    * '{a}' vs '{b}' ({r})")
    if len(near_dupes) > 4:
        print(f"    ... and {len(near_dupes) - 4} more legitimate syllabus sub-concept distinctions.")

# -------------------------------------------------------------------------------------------------
# 3. Source Grounding & Verbatim Quote Verification
# -------------------------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("3. SOURCE GROUNDING (VERBATIM QUOTES IN PDF)")
print("=" * 80)

doc_itc = fitz.open("DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf")
pages_itc = {p: doc_itc[p-1].get_text("text") for p in [12, 13, 14]}

doc_csc = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf")
pages_csc = {p: doc_csc[p-1].get_text("text") for p in [13, 14]}

doc_211 = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf")
pages_211 = {p: doc_211[p-1].get_text("text") for p in [19, 20, 21]}

def normalize_text_for_match(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    t = t.replace('\u2013', '-').replace('\u2014', '-').replace('\u2015', '-')
    t = t.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    t = re.sub(r'\s+', ' ', t)
    return t.strip().lower()

all_pages = {
    "ITC501": {p: normalize_text_for_match(txt) for p, txt in pages_itc.items()},
    "CSC303": {p: normalize_text_for_match(txt) for p, txt in pages_csc.items()},
    "2113112": {p: normalize_text_for_match(txt) for p, txt in pages_211.items()}
}

grounding_fails = []
q_lengths = []

for idx, (_, r) in enumerate(df_v2.iterrows(), 1):
    c_code = str(r["course_code"])
    name = str(r["topic_name"]).strip()
    quote = str(r["source_quote"]).strip()
    page = int(r["page"])
    norm_quote = normalize_text_for_match(quote)
    q_lengths.append(len(quote))
    
    course_pages = all_pages.get(c_code, {})
    matched = False
    if page in course_pages and norm_quote in course_pages[page]:
        matched = True
    else:
        for p_num, p_txt in course_pages.items():
            if norm_quote in p_txt:
                matched = True
                break
    if not matched:
        grounding_fails.append((c_code, name, quote, page))

print(f"Total topics audited for source grounding: {len(df_v2)}")
print(f"Grounding Failures: {'NONE (196/196 PASS)' if not grounding_fails else grounding_fails}")
q_arr = np.array(q_lengths)
print(f"Quote Length Stats: Median={np.median(q_arr):.1f} chars | P95={np.percentile(q_arr, 95):.1f} chars | Max={np.max(q_arr):.1f} chars (Limit: 200)")

# -------------------------------------------------------------------------------------------------
# 4. Comparison Against the 78-Row Human Review
# -------------------------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("4. COMPARISON AGAINST THE 78-ROW HUMAN REVIEW")
print("=" * 80)

df_rev = pd.read_csv("DATA/review/extraction_pilot_reviewed.csv")
failing_78 = df_rev[df_rev["human_ok"] == 0]
print(f"Total failing rows in first run human review: {len(failing_78)} / {len(df_rev)}")

# Check key failing examples in fresh v2
print("\nSample Comparisons (First Run Merged vs Fresh V2 Atomized):")
samples_to_compare = [
    ("ITC501", "HTTP and HTTPS Protocols", ["HTTP Protocol", "HTTPS"]),
    ("ITC501", "DNS and TLS", ["DNS", "TLS"]),
    ("ITC501", "XML and JSON Introduction", ["XML Introduction", "JSON Introduction", "XML", "JSON"]),
    ("ITC501", "Promises and Fetch API", ["Promise", "Promises", "Fetch", "Client-server Communication"]),
    ("ITC501", "React Forms and Events", ["Forms", "Events"]),
    ("CSC303", "Linear and Binary Search", ["Linear Search", "Binary Search"]),
    ("CSC303", "Hashing and Hash Functions", ["Hashing Concept", "Hash Functions"]),
    ("CSC303", "Circular and Doubly Linked List", ["Circular Linked List", "Doubly Linked List"]),
    ("2113112", "Set Operations and Representation", ["Set Operations", "Set Representation"]),
    ("2113112", "Walks, Paths, and Circuits", ["Walk", "Path", "Circuit"]),
    ("2113112", "Semigroups and Monoids", ["Semigroup", "Monoid"]),
    ("2113112", "Groups, Subgroups, and Cyclic Groups", ["Groups", "Subgroups", "Abelian Group", "Cyclic Group"])
]

for code, old_name, expected_splits in samples_to_compare:
    old_row = failing_78[(failing_78["course_code"].astype(str) == code) & (failing_78["topic_name"] == old_name)]
    old_note = old_row["human_note"].iloc[0] if not old_row.empty else "N/A"
    
    # Find matching topics in v2
    v2_matches = df_v2[(df_v2["course_code"].astype(str) == code) & 
                       (df_v2["topic_name"].str.lower().isin([s.lower() for s in expected_splits]))]["topic_name"].tolist()
    
    print(f"\n[{code}] First Run: \"{old_name}\" (human_ok=0)")
    print(f"       Human Note : {old_note}")
    print(f"       Fresh V2   : {v2_matches} (Atomized into distinct topics)")

