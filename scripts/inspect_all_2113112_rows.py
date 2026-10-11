import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

df_v2 = pd.read_csv("DATA/review/extraction_pilot_v2.csv")
df_sample = pd.read_csv("DATA/review/extraction_pilot_v2_review_sample_labeled.csv")

df_v2["course_code"] = df_v2["course_code"].astype(str)
df_sample["course_code"] = df_sample["course_code"].astype(str)

df_v2_clean = df_v2.drop(columns=['human_ok'], errors='ignore')
merged = df_v2_clean.merge(
    df_sample[['course_code', 'unit', 'topic_name', 'human_ok', 'human_note']],
    on=['course_code', 'unit', 'topic_name'],
    how='left'
)

c211_rows = merged[merged["course_code"] == "2113112"]
print(f"Total 2113112 rows: {len(c211_rows)}")

for idx, r in c211_rows.iterrows():
    lbl = f"[Sample: human_ok={int(r['human_ok'])}]" if pd.notna(r['human_ok']) else "[Not in sample]"
    print(f"Row {idx:2d} | Mod: {r['unit']} | Topic: '{r['topic_name']}' | Quote: '{r['source_quote']}' | p.{r['page']} | {lbl}")
    if pd.notna(r['human_note']) and r['human_note']:
        print(f"       Note: {r['human_note']}")

