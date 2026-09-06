import pandas as pd
import re

df = pd.read_csv('Cleaned_Files/labeling_dataset.csv')
lab_proj_re = re.compile(r'\b(mini[\s\-]?project|lab\b|laboratory|workshop|capstone)\b', re.I)
theory_df = df[~df['course_name'].str.contains(lab_proj_re, na=False)].copy()

# Inspect concepts that contain obvious noise markers
noise_pats = [
    re.compile(r'self[\s\-]learning', re.I),
    re.compile(r'questions?\s+(need|compulsory|solve|paper|out\s+of)', re.I),
    re.compile(r'marks', re.I),
    re.compile(r'text\s*books?|references?', re.I),
    re.compile(r'university\s+of\s+mumbai', re.I),
    re.compile(r'addison|oreilly|pearson|mcgraw|wiley|bpb|prentice', re.I),
    re.compile(r'students?\s+(are|can|should|shall|must)', re.I),
    re.compile(r'^[a-z]'),
    re.compile(r'\b(and|or|of|in|to|for|with)\s*$', re.I),
    re.compile(r'\(.*?\b(proof|only|without)\b', re.I),
    re.compile(r'q\d+[:.]', re.I),
    re.compile(r'["\u201c\u201d\u2018\u2019\u2015]', re.I),
    re.compile(r'[A-Z][a-z]+.*&\s*(Dr\.|Prof\.)?\s*[A-Z][a-z]+'),
]

noisy_rows = []
for idx, r in theory_df.iterrows():
    a = str(r['concept_a'])
    b = str(r['concept_b'])
    matched = []
    for pat in noise_pats:
        if pat.search(a) or pat.search(b):
            matched.append(pat.pattern)
    if len(a.split()) > 10 or len(b.split()) > 10:
        matched.append("word_count_gt_10")
    if matched:
        noisy_rows.append((idx, r['course_name'], a, b, r['label'], matched))

print(f"Total theory rows: {len(theory_df)}")
print(f"Noisy theory rows found: {len(noisy_rows)}")
print(f"Clean theory rows: {len(theory_df) - len(noisy_rows)}")

with open('scripts/theory_noise_samples.txt', 'w', encoding='utf-8') as f:
    for idx, course, a, b, lbl, m in noisy_rows[:50]:
        f.write(f"[{course}] '{a}' -> '{b}' [label={lbl}]\n")
        f.write(f"   Patterns: {m}\n")

print("Wrote scripts/theory_noise_samples.txt")

