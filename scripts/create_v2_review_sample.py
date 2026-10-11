import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load full v2 file
v2_path = "DATA/review/extraction_pilot_v2.csv"
df = pd.read_csv(v2_path)
print(f"Loaded {len(df)} rows from '{v2_path}'.")

# Sample 78 rows flat random with seed 42
# Using pandas df.sample(n=78, random_state=42)
sample_df = df.sample(n=78, random_state=42).copy()

# Add human_note column, ensuring both human_ok and human_note are strictly blank
sample_df["human_ok"] = ""
sample_df["human_note"] = ""

# Ensure columns
cols = ['course_code', 'title', 'semester', 'unit', 'topic_name', 'source_quote', 'page', 'human_ok', 'human_note']
sample_df = sample_df[cols]

# Write to DATA/review/extraction_pilot_v2_review_sample.csv
out_path = "DATA/review/extraction_pilot_v2_review_sample.csv"
sample_df.to_csv(out_path, index=False)

print(f"\nWritten {len(sample_df)} rows to '{out_path}'.")
print(f"human_ok strictly blank: {bool((sample_df['human_ok'] == '').all())}")
print(f"human_note strictly blank: {bool((sample_df['human_note'] == '').all())}")

print("\n--- Sample Course Distribution ---")
course_counts = sample_df['course_code'].value_counts()
for c, cnt in course_counts.items():
    print(f"  {c:<8}: {cnt:>2} topics ({cnt/len(sample_df):.1%})")

print("\n--- Sample Course & Module Distribution ---")
mod_counts = sample_df.groupby(['course_code', 'unit'], sort=False).size()
for (c, u), cnt in mod_counts.items():
    print(f"  [{c}] {u:<45} : {cnt:>2} topics")

