import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv("DATA/review/extraction_pilot_reviewed.csv")
failing = df[df['human_ok'] == 0]

print("=== Failing Rows 1 to 15 ===")
for idx, (_, r) in enumerate(failing.iloc[:15].iterrows(), 1):
    note = str(r['human_note']) if pd.notna(r['human_note']) else "(empty)"
    print(f"{idx:>2}. [{r['course_code']}] [{r['unit']}] \"{r['topic_name']}\"")
    print(f"    Source Quote: \"{r['source_quote']}\"")
    print(f"    Human Note:   {note}")

