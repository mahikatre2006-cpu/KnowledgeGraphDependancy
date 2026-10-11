import pandas as pd
import numpy as np
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("1. VERIFY V2 FILE AND REPORTED COUNTS")
print("=" * 80)

v2_path = "DATA/review/extraction_pilot_v2.csv"
df_v2 = pd.read_csv(v2_path)
print(f"Total rows in {v2_path}: {len(df_v2)}")
print("Counts by course_code in V2:")
v2_counts = df_v2['course_code'].astype(str).value_counts()
for code, count in v2_counts.items():
    print(f"  {code}: {count}")

print("\n" + "=" * 80)
print("2. INSPECT AND VALIDATE SUPPLIED LABELED SAMPLE")
print("=" * 80)

sample_labeled_path = "DATA/review/extraction_pilot_v2_review_sample_labeled.csv"
df_sample = pd.read_csv(sample_labeled_path)
print(f"Total rows in {sample_labeled_path}: {len(df_sample)}")
print(f"Columns: {list(df_sample.columns)}")

print("\nLabel distribution (human_ok):")
print(df_sample['human_ok'].value_counts(dropna=False))
h1_count = (df_sample['human_ok'] == 1).sum()
h0_count = (df_sample['human_ok'] == 0).sum()
hna_count = df_sample['human_ok'].isna().sum()
print(f"human_ok == 1: {h1_count}")
print(f"human_ok == 0: {h0_count}")
print(f"human_ok is NA / blank: {hna_count}")

print("\nRows with human_ok == 0:")
zero_rows = df_sample[df_sample['human_ok'] == 0]
for idx, r in zero_rows.iterrows():
    print(f"  [{r['course_code']}] '{r['topic_name']}' ({r['unit']})")
    print(f"    Note: {r['human_note']}")

print("\n" + "=" * 80)
print("3. VERIFY MATCHING BETWEEN LABELED SAMPLE AND EXTRACTION_PILOT_V2.CSV")
print("=" * 80)

def norm_str(s):
    if pd.isna(s):
        return ""
    return re.sub(r'\s+', ' ', str(s)).strip().lower()

matched_indices_in_v2 = []
unmatched = []
ambiguous = []

for s_idx, s_row in df_sample.iterrows():
    s_code = norm_str(s_row['course_code'])
    s_unit = norm_str(s_row['unit'])
    s_topic = norm_str(s_row['topic_name'])
    s_quote = norm_str(s_row['source_quote'])
    s_page = int(s_row['page']) if not pd.isna(s_row['page']) else -1
    
    # Match in df_v2
    matches = []
    for v_idx, v_row in df_v2.iterrows():
        v_code = norm_str(v_row['course_code'])
        v_unit = norm_str(v_row['unit'])
        v_topic = norm_str(v_row['topic_name'])
        v_quote = norm_str(v_row['source_quote'])
        v_page = int(v_row['page']) if not pd.isna(v_row['page']) else -1
        
        if (s_code == v_code and 
            s_unit == v_unit and 
            s_topic == v_topic and 
            s_quote == v_quote and 
            s_page == v_page):
            matches.append(v_idx)
            
    if len(matches) == 1:
        matched_indices_in_v2.append(matches[0])
    elif len(matches) == 0:
        unmatched.append((s_idx, s_row))
    else:
        ambiguous.append((s_idx, s_row, matches))

print(f"Total sample rows matched uniquely to V2: {len(matched_indices_in_v2)} / {len(df_sample)}")
print(f"Unmatched rows: {len(unmatched)}")
for s_idx, r in unmatched:
    print(f"  Unmatched: row {s_idx}: [{r['course_code']}] '{r['topic_name']}' quote='{r['source_quote']}' page={r['page']}")

print(f"Ambiguous matches: {len(ambiguous)}")
for s_idx, r, ms in ambiguous:
    print(f"  Ambiguous: row {s_idx}: [{r['course_code']}] '{r['topic_name']}' matched V2 rows {ms}")

