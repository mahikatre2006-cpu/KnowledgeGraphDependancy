import json
import re
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv("DATA/review/extraction_pilot_v2.csv")

print(f"Total rows in extraction_pilot_v2.csv: {len(df)}")

# 1. Investigate ITC501 Module II (19 topics)
print("\n" + "="*80)
print("ITC501 Module II (Java script:)")
print("="*80)
itc_m2 = df[(df["course_code"] == "ITC501") & (df["unit"].str.contains("Module II", case=False))]
for idx, (_, r) in enumerate(itc_m2.iterrows(), 1):
    print(f"{idx:>2}. '{r['topic_name']}' | Quote: '{r['source_quote']}' | Page: {r['page']}")

# 2. Investigate ITC501 Module III (15 topics)
print("\n" + "="*80)
print("ITC501 Module III (React fundamentals)")
print("="*80)
itc_m3 = df[(df["course_code"] == "ITC501") & (df["unit"].str.contains("Module III", case=False))]
for idx, (_, r) in enumerate(itc_m3.iterrows(), 1):
    print(f"{idx:>2}. '{r['topic_name']}' | Quote: '{r['source_quote']}' | Page: {r['page']}")

# 3. Investigate 2113112 Module VI (18 topics)
print("\n" + "="*80)
print("2113112 Module VI (Graph Theory)")
print("="*80)
dmath_m6 = df[(df["course_code"].astype(str) == "2113112") & (df["unit"].str.contains("Graph Theory|VI", case=False))]
for idx, (_, r) in enumerate(dmath_m6.iterrows(), 1):
    print(f"{idx:>2}. '{r['topic_name']}' | Quote: '{r['source_quote']}' | Page: {r['page']}")

# 4. Check XML / JSON topics in ITC501
print("\n" + "="*80)
print("XML / JSON topics in ITC501")
print("="*80)
xml_json = df[(df["course_code"] == "ITC501") & (df["topic_name"].str.contains("XML|JSON", case=False))]
for idx, (_, r) in enumerate(xml_json.iterrows(), 1):
    print(f"{idx:>2}. [{r['unit']}] '{r['topic_name']}' | Quote: '{r['source_quote']}' | Page: {r['page']}")

# 5. Full near-duplicate pairs across each course
print("\n" + "="*80)
print("DETAILED NEAR-DUPLICATE PAIRS ACROSS ALL COURSES")
print("="*80)
for course in ["ITC501", "CSC303", "2113112"]:
    cdf = df[df["course_code"].astype(str) == course]
    topics = cdf.to_dict('records')
    print(f"\n--- Course {course} ({len(topics)} topics) ---")
    near_pairs = []
    for i in range(len(topics)):
        for j in range(i+1, len(topics)):
            t1, t2 = topics[i], topics[j]
            n1 = t1["topic_name"].lower()
            n2 = t2["topic_name"].lower()
            w1 = set(n1.split())
            w2 = set(n2.split())
            if n1 != n2:
                overlap = len(w1 & w2) / max(len(w1), len(w2))
                if n1 in n2 or n2 in n1:
                    near_pairs.append((t1, t2, "substring containment", overlap))
                elif overlap >= 0.5:
                    near_pairs.append((t1, t2, f"token overlap {overlap:.1%}", overlap))
    print(f"Total near-duplicate pairs found: {len(near_pairs)}")
    for t1, t2, reason, ov in near_pairs:
        print(f"  * [{t1['unit']}] '{t1['topic_name']}' (quote: '{t1['source_quote']}')\n    vs [{t2['unit']}] '{t2['topic_name']}' (quote: '{t2['source_quote']}')\n    Reason: {reason}\n")

