import json
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open("DATA/processed/gemini_cache/2113112_v2.json", "r", encoding="utf-8") as f:
    v2_data = json.load(f)
v2_topics = v2_data["topics"]

v3_df = pd.read_csv("DATA/review/extraction_pilot_2113112_v3.csv")
v3_topics = v3_df["topic_name"].tolist()

print(f"v2 topic count: {len(v2_topics)}")
print(f"v3 topic count: {len(v3_topics)}")

v2_names = [t["name"] for t in v2_topics]

# Find removed topics from v2
removed = [t for t in v2_topics if t["name"] not in v3_topics]
print(f"\nRemoved / modified from v2 ({len(removed)} topics):")
for t in removed:
    print(f"  [{t['unit']}] '{t['name']}' (quote: '{t['source_quote']}', p. {t['page']})")

# Find new topics in v3
new_in_v3 = [t for t in v3_topics if t not in v2_names]
print(f"\nNew / composite in v3 ({len(new_in_v3)} topics):")
for name in new_in_v3:
    r = v3_df[v3_df["topic_name"] == name].iloc[0]
    print(f"  [{r['unit']}] '{name}' (quote: '{r['source_quote']}', p. {r['page']})")

