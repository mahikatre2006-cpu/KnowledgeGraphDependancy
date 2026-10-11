import json
import random
import re
from collections import defaultdict
import pandas as pd

with open("DATA/processed/gemini_cache/2113112_v2.json", "r", encoding="utf-8") as f:
    data = json.load(f)

topics = data["topics"]
print(f"Total topics in 2113112_v2: {len(topics)}")

# 1. Topic count per module
mod_counts = defaultdict(list)
for t in topics:
    mod_counts[t["unit"]].append(t)

print("\n--- Topic count per module ---")
for mod, t_list in sorted(mod_counts.items()):
    print(f"  {mod:<45}: {len(t_list)} topics")

# 2. 15 flat-random topics (seed 42) with quotes
random.seed(42)
sampled_indices = sorted(random.sample(range(len(topics)), 15))
print("\n--- 15 Flat-Random Topics (seed 42) with Quotes ---")
for i, idx in enumerate(sampled_indices, 1):
    t = topics[idx]
    print(f"{i:>2}. [{t['unit']}]")
    print(f"    Name : '{t['name']}'")
    print(f"    Quote: '{t['source_quote']}' (p. {t['page']})")

# 3. Exact-duplicate and near-duplicate names
print("\n--- Exact and Near Duplicate Names ---")
names = [t["name"] for t in topics]
seen_exact = set()
exact_dupes = []
for n in names:
    norm = re.sub(r'\s+', ' ', n.strip().lower())
    if norm in seen_exact:
        exact_dupes.append(n)
    seen_exact.add(norm)
print(f"Exact duplicates (case/whitespace normalized): {exact_dupes if exact_dupes else 'None'}")

# Near-duplicates: check substring or high token overlap
near_dupes = []
for i in range(len(topics)):
    for j in range(i+1, len(topics)):
        n1 = topics[i]["name"].lower()
        n2 = topics[j]["name"].lower()
        w1 = set(n1.split())
        w2 = set(n2.split())
        # check if one contains the other or token overlap > 70%
        if n1 != n2:
            if n1 in n2 or n2 in n1:
                near_dupes.append((topics[i]["unit"], topics[i]["name"], topics[j]["unit"], topics[j]["name"], "substring containment"))
            elif len(w1 & w2) / max(len(w1), len(w2)) >= 0.6:
                near_dupes.append((topics[i]["unit"], topics[i]["name"], topics[j]["unit"], topics[j]["name"], "token overlap"))

print(f"Near-duplicates found ({len(near_dupes)} pairs):")
for u1, name1, u2, name2, reason in near_dupes:
    print(f"  * '{name1}' vs '{name2}' ({reason}) [{u1}]")

# 4. 8-60 quality-gate result for the 62
gate_pass = 8 <= len(topics) <= 60
print(f"\n--- Quality Gate (8-60 topics) ---")
print(f"Gate check: {'PASS' if gate_pass else 'FAIL'} (Count = {len(topics)} > 60 limit)")

