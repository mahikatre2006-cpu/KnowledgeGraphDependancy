import json
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# 1. Exact cached baseline:
with open("DATA/processed/gemini_cache/257ca70b7c2c58a2070c025a92525688482177de66531f034f4e3bb2ba5d4c74.json", "r", encoding="utf-8") as f:
    orig_cache = json.load(f)
baseline_raw = orig_cache["topics"]

# The 25 accepted topics in reviewed CSV:
df_rev = pd.read_csv("DATA/review/extraction_pilot_reviewed.csv")
baseline_accepted_names = df_rev[df_rev["course_code"].astype(str) == "2113112"]["topic_name"].tolist()

# 2. 62-topic version:
with open("DATA/processed/gemini_cache/2113112_v2.json", "r", encoding="utf-8") as f:
    v2_cache = json.load(f)
v2_topics = v2_cache["topics"]
v2_names = [t["name"] for t in v2_topics]

print("=" * 80)
print("EXACT TOPIC-LEVEL DIFF: BASELINE (25/26) vs V2 (62 TOPICS)")
print("=" * 80)

# Per-module topic counts
print("\n--- Per-Module Topic Counts ---")
modules = [
    "Module I: Crisp Set Theory and Logic",
    "Module II: Mathematical Relations",
    "Module III: Functions",
    "Module IV: Counting",
    "Module V: Algebraic Structures",
    "Module VI: Graph Theory"
]

for m in modules:
    b_count = len([t for t in baseline_raw if t["unit"] == m])
    b_acc_count = len([n for n in baseline_accepted_names if any(t["name"] == n and t["unit"] == m for t in baseline_raw)])
    v2_count = len([t for t in v2_topics if t["unit"] == m])
    print(f"{m:<45} | Baseline: {b_count:>2} raw / {b_acc_count:>2} acc | v2: {v2_count:>2} topics (Delta: {v2_count - b_count:+d})")

print("\n--- Topic-Level Diff by Module ---")
for m in modules:
    b_m_topics = [t["name"] for t in baseline_raw if t["unit"] == m]
    v2_m_topics = [t["name"] for t in v2_topics if t["unit"] == m]
    
    print(f"\n[{m}]")
    print(f"  Baseline ({len(b_m_topics)} topics): {b_m_topics}")
    print(f"  v2       ({len(v2_m_topics)} topics): {v2_m_topics}")
    
    added = [t for t in v2_m_topics if t not in b_m_topics]
    removed = [t for t in b_m_topics if t not in v2_m_topics]
    retained = [t for t in b_m_topics if t in v2_m_topics]
    
    print(f"  -> Retained unchanged ({len(retained)}): {retained}")
    print(f"  -> Removed / Split    ({len(removed)}):  {removed}")
    print(f"  -> Added / Atomized   ({len(added)}):    {added}")


