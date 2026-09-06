import pandas as pd

df = pd.read_csv('data/label_audit_flagged.csv')
sub = df.iloc[1870:1905]
with open('scripts/audit_inspection_1888.txt', 'w', encoding='utf-8') as f:
    for i, r in sub.iterrows():
        f.write(f"Index {i} (CSV Line {i+2}): [{r['flag_reason']}] '{r['concept_a']}' -> '{r['concept_b']}' (Course: {r['course_name']}, Label: {r['label']})\n")
        f.write(f"    All reasons: {r['all_flag_reasons']}\n")
print("Wrote scripts/audit_inspection_1888.txt")

