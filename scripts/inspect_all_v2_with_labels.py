import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

df_v2 = pd.read_csv("DATA/review/extraction_pilot_v2.csv")
df_sample = pd.read_csv("DATA/review/extraction_pilot_v2_review_sample_labeled.csv")

df_v2["course_code"] = df_v2["course_code"].astype(str)
df_sample["course_code"] = df_sample["course_code"].astype(str)

# Drop human_ok from df_v2 if present before merging
df_v2_clean = df_v2.drop(columns=['human_ok'], errors='ignore')

merged = df_v2_clean.merge(
    df_sample[['course_code', 'unit', 'topic_name', 'human_ok', 'human_note', 'audit_evidence']],
    on=['course_code', 'unit', 'topic_name'],
    how='left'
)

print(f"Total rows in v2: {len(df_v2)}")
print(f"Sampled rows with human_ok: {merged['human_ok'].notna().sum()}")

for code in ["ITC501", "CSC303", "2113112"]:
    cdf = merged[merged["course_code"] == code]
    print(f"\n==================== COURSE {code} (Total: {len(cdf)}) ====================")
    for unit, ugroup in cdf.groupby("unit", sort=False):
        print(f"\n  --- {unit} ({len(ugroup)} topics) ---")
        for idx, r in ugroup.iterrows():
            lbl = f"[human_ok={int(r['human_ok'])}]" if pd.notna(r['human_ok']) else "[UNSAMPLED]"
            note = f" -- NOTE: {r['human_note']}" if pd.notna(r['human_note']) and r['human_note'] else ""
            print(f"    {r['topic_name']:<35} | Quote: '{r['source_quote']}' (p.{r['page']}) {lbl}{note}")

