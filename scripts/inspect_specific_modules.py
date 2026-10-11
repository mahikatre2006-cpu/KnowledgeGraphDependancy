import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv("DATA/review/extraction_pilot_v2.csv")

print("=== 1. ITC501 Module II (19 topics) ===")
itc_m2 = df[(df["course_code"] == "ITC501") & (df["unit"].str.contains("Module II", case=False))]
for idx, (_, r) in enumerate(itc_m2.iterrows(), 1):
    print(f"{idx:>2}. '{r['topic_name']}' | Quote: '{r['source_quote']}' | Page: {r['page']}")

print("\n=== 2. ITC501 Module III (15 topics) ===")
itc_m3 = df[(df["course_code"] == "ITC501") & (df["unit"].str.contains("Module III", case=False))]
for idx, (_, r) in enumerate(itc_m3.iterrows(), 1):
    print(f"{idx:>2}. '{r['topic_name']}' | Quote: '{r['source_quote']}' | Page: {r['page']}")

print("\n=== 3. 2113112 Module VI (18 topics) ===")
dmath_m6 = df[(df["course_code"].astype(str) == "2113112") & (df["unit"].str.contains("Graph Theory|VI", case=False))]
for idx, (_, r) in enumerate(dmath_m6.iterrows(), 1):
    print(f"{idx:>2}. '{r['topic_name']}' | Quote: '{r['source_quote']}' | Page: {r['page']}")

print("\n=== 4. XML / JSON in ITC501 ===")
xml_json = df[(df["course_code"] == "ITC501") & (df["topic_name"].str.contains("XML|JSON", case=False))]
for idx, (_, r) in enumerate(xml_json.iterrows(), 1):
    print(f"{idx:>2}. [{r['unit']}] '{r['topic_name']}' | Quote: '{r['source_quote']}' | Page: {r['page']}")

