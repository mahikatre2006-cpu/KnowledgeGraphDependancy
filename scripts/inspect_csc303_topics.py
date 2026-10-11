import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv("DATA/review/extraction_pilot_v2.csv")
csc = df[df["course_code"] == "CSC303"]

print(f"Total topics in CSC303: {len(csc)}")
for idx, (_, r) in enumerate(csc.iterrows(), 1):
    print(f"{idx:>2}. [{r['unit']}] '{r['topic_name']}' | Quote: '{r['source_quote']}' | Page: {r['page']}")

