import json
import re
import fitz
import numpy as np
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load v2 topics
with open("DATA/processed/gemini_cache/2113112_v2.json", "r", encoding="utf-8") as f:
    data_v2 = json.load(f)
topics_v2 = data_v2["topics"]

# The 8 dropped topics (deduplicated / subsumed)
dropped_8 = {
    'Universal and Empty Sets',
    'Proof by deduction',
    'Proof by cases',
    'Proof by exhaustion',
    'Poset',
    'Types of Lattices',
    'Sub lattice',
    'Recurrence relations'
}

# In this reassessed version, Walk, Path, Circuit and Connected Graphs, Disconnected Graph are NOT merged!
# They remain distinct individual topics directly from v2.
reassessed_topics = [t for t in topics_v2 if t["name"] not in dropped_8]

print(f"Total topics in reassessed version: {len(reassessed_topics)}")
assert len(reassessed_topics) == 54, f"Expected 54 topics, got {len(reassessed_topics)}"

# 1. Quality Gate Check (8-60)
gate_pass = 8 <= len(reassessed_topics) <= 60
print(f"Quality Gate [8-60 topics]: {'PASS' if gate_pass else 'FAIL'} ({len(reassessed_topics)} topics)")

# 2. Per-module topic distribution
mod_dist = {}
for t in reassessed_topics:
    u = t["unit"]
    mod_dist[u] = mod_dist.get(u, 0) + 1

print("\n--- Per-Module Topic Counts ---")
for mod, count in sorted(mod_dist.items()):
    status = "OK" if count >= 3 else "WARNING (< 3)"
    print(f"  {mod:<45} : {count:>2} topics [{status}]")

# 3. Exact Duplicate Check
seen_exact = {}
exact_dupes = []
for idx, t in enumerate(reassessed_topics):
    norm = re.sub(r'\s+', ' ', t["name"].strip().lower())
    if norm in seen_exact:
        exact_dupes.append((t["name"], seen_exact[norm]))
    seen_exact[norm] = idx

print(f"\nExact duplicates check: {'PASS (0 duplicates)' if not exact_dupes else 'FAIL: ' + str(exact_dupes)}")

# 4. Near-Duplicate Check
near_dupes = []
for i in range(len(reassessed_topics)):
    for j in range(i+1, len(reassessed_topics)):
        n1 = reassessed_topics[i]["name"].lower()
        n2 = reassessed_topics[j]["name"].lower()
        w1 = set(n1.split())
        w2 = set(n2.split())
        if n1 != n2:
            # check token overlap or substring
            if n1 in n2 or n2 in n1:
                near_dupes.append((reassessed_topics[i]["name"], reassessed_topics[j]["name"], "substring containment"))
            elif len(w1 & w2) / max(len(w1), len(w2)) >= 0.6:
                near_dupes.append((reassessed_topics[i]["name"], reassessed_topics[j]["name"], "token overlap >= 60%"))

print(f"\nNear-duplicates check ({len(near_dupes)} pairs found):")
for n1, n2, reason in near_dupes:
    print(f"  * '{n1}' vs '{n2}' ({reason})")

# 5. Complete Topic-Quality Checks against PDF
pdf_path = "DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf"
doc = fitz.open(pdf_path)
page_texts = {p: doc[p-1].get_text("text") for p in [19, 20, 21]}

def normalize_text_for_match(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    t = t.replace('\u2013', '-').replace('\u2014', '-').replace('\u2015', '-')
    t = t.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    t = re.sub(r'\s+', ' ', t)
    return t.strip().lower()

norm_pages = {p: normalize_text_for_match(txt) for p, txt in page_texts.items()}
banned = ['mark', 'marks', 'credit', 'credits', 'hour', 'hours', 'textbook', 'reference', 'syllabus', 'assessment', 'prerequisite']

quote_lens = []
quality_issues = []

for idx, t in enumerate(reassessed_topics, 1):
    name = t["name"].strip()
    quote = t["source_quote"].strip()
    page = t["page"]
    words = name.split()
    norm_name = normalize_text_for_match(name)
    norm_quote = normalize_text_for_match(quote)
    quote_lens.append(len(quote))
    
    # Word count: 1 to 8 words
    if len(words) < 1 or len(words) > 8:
        quality_issues.append((name, f"Word count out of bounds ({len(words)})"))
    # Char count: < 100
    if len(name) >= 100:
        quality_issues.append((name, f"Name >= 100 chars ({len(name)})"))
    # Quote check
    if not quote:
        quality_issues.append((name, "Empty quote"))
    elif len(quote) > 200:
        quality_issues.append((name, f"Quote > 200 chars ({len(quote)})"))
    # Page match
    matched = False
    if page in norm_pages and norm_quote in norm_pages[page]:
        matched = True
    else:
        for p, ptxt in norm_pages.items():
            if norm_quote in ptxt:
                matched = True
                break
    if not matched:
        quality_issues.append((name, f"Quote not found on page {page}"))
    # Banned words
    if any(re.search(r'\b' + re.escape(b) + r'\b', norm_name) for b in banned):
        quality_issues.append((name, "Contains banned administrative words"))

print(f"\nTopic-Quality Issues: {'NONE (ALL PASS)' if not quality_issues else quality_issues}")
q_arr = np.array(quote_lens)
print(f"Quote stats: Median={np.median(q_arr):.1f}, P95={np.percentile(q_arr, 95):.1f}, Max={np.max(q_arr):.1f} chars (Limit: 200)")

