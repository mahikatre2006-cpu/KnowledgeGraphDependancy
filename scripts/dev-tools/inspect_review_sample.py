import pandas as pd

df = pd.read_csv('data/review_sample.csv')
with open('scripts/review_sample_preview.txt', 'w', encoding='utf-8') as f:
    for idx, r in df.iterrows():
        b = str(r['bucket'])
        a = str(r['concept_a'])
        c = str(r['concept_b'])
        cn = str(r['course_name'])
        f.write(f"{idx+1:3d}. [{b}] '{a}' -> '{c}' ({cn})\n")
print(f"Wrote {len(df)} rows to scripts/review_sample_preview.txt")

