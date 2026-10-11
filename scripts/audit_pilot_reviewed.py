import pandas as pd
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv("DATA/review/extraction_pilot_reviewed.csv")

print(f"Total rows: {len(df)}")
print(f"Columns: {list(df.columns)}")

print("\n--- Per-Course Counts ---")
for course in sorted(df['course_code'].unique()):
    cdf = df[df['course_code'] == course]
    c_1 = (cdf['human_ok'] == 1).sum()
    c_0 = (cdf['human_ok'] == 0).sum()
    c_blank = cdf['human_ok'].isna().sum()
    tot = len(cdf)
    fail_rate = c_0 / tot if tot > 0 else 0
    print(f"Course {course}: Total={tot}, human_ok=1: {c_1}, human_ok=0: {c_0}, blank: {c_blank}, Fail Rate: {fail_rate:.1%}")

total_1 = (df['human_ok'] == 1).sum()
total_0 = (df['human_ok'] == 0).sum()
total_blank = df['human_ok'].isna().sum()
overall_fail_rate = total_0 / len(df) if len(df) > 0 else 0

print("\n--- Overall Summary ---")
print(f"Total human_ok=1: {total_1}")
print(f"Total human_ok=0: {total_0}")
print(f"Total blank:      {total_blank}")
print(f"Overall Failure Count: {total_0}")
print(f"Overall Failure Rate:  {overall_fail_rate:.1%} ({total_0}/{len(df)})")

print("\n--- Failing Rows (human_ok=0) [1 to 15] ---")
failing = df[df['human_ok'] == 0]
for idx, (_, r) in enumerate(failing.iloc[:15].iterrows(), 1):
    note = str(r['human_note']) if pd.notna(r['human_note']) else "(empty)"
    print(f"{idx:>2}. [{r['course_code']}] [{r['unit']}] \"{r['topic_name']}\"")
    print(f"    Source Quote: \"{r['source_quote']}\"")
    print(f"    Human Note:   {note}")

print("\n--- Failing Rows (human_ok=0) [16 to 39] ---")
for idx, (_, r) in enumerate(failing.iloc[15:].iterrows(), 16):
    note = str(r['human_note']) if pd.notna(r['human_note']) else "(empty)"
    print(f"{idx:>2}. [{r['course_code']}] [{r['unit']}] \"{r['topic_name']}\"")
    print(f"    Source Quote: \"{r['source_quote']}\"")
    print(f"    Human Note:   {note}")

print("\n--- Module-Level Failure Breakdown ---")
mod_fails = failing.groupby(['course_code', 'unit']).size().reset_index(name='fail_count')
mod_totals = df.groupby(['course_code', 'unit']).size().reset_index(name='total_topics')
mod_merged = pd.merge(mod_totals, mod_fails, on=['course_code', 'unit'], how='left').fillna(0)
mod_merged['fail_count'] = mod_merged['fail_count'].astype(int)
mod_merged['fail_rate'] = mod_merged['fail_count'] / mod_merged['total_topics']
mod_merged = mod_merged.sort_values(by=['course_code', 'unit'])

for _, r in mod_merged.iterrows():
    print(f"[{r['course_code']}] {r['unit']:<45} : {r['fail_count']:>2}/{r['total_topics']:>2} failed ({r['fail_rate']:.1%})")
