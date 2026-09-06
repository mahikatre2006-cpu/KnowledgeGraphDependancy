import pandas as pd
import re

df = pd.read_csv('Cleaned_Files/labeling_dataset.csv')
lab_proj_re = re.compile(r'\b(mini[\s\-]?project|lab\b|laboratory|workshop|capstone)\b', re.I)
theory_df = df[~df['course_name'].str.contains(lab_proj_re, na=False)].copy()

noise_pats = [
    re.compile(r'self[\s\-]learning', re.I),
    re.compile(r'learning\s+topics?', re.I),
    re.compile(r'questions?\s+(need|compulsory|solve|paper|out\s+of|will\s+be)', re.I),
    re.compile(r'marks', re.I),
    re.compile(r'text\s*books?|references?', re.I),
    re.compile(r'university\s+of\s+mumbai', re.I),
    re.compile(r'addison|oreilly|pearson|mcgraw|wiley|bpb|prentice|khanna|narosa|cengage|elsevier|springer', re.I),
    re.compile(r'students?\s+(are|can|should|shall|must)', re.I),
    re.compile(r'^[a-z]'),
    re.compile(r'\b(and|or|of|in|to|for|with)\s*$', re.I),
    re.compile(r'\(.*?\b(proof|only|without)\b', re.I),
    re.compile(r'q\d+[:.]', re.I),
    re.compile(r'["\u201c\u201d\u2018\u2019\u2015]', re.I),
    re.compile(r'[A-Z][a-z]+.*&\s*(Dr\.|Prof\.)?\s*[A-Z][a-z]+'),
    re.compile(r'\b(Anish Nath|Singh Rathore|Associate Dean|Robert C\. Martin)\b'),
    re.compile(r'\b(internal\s*assessment|end\s*sem|term\s*work|part\s*\(a\)|note\s*for|all\s*cos)\b', re.I),
]

clean_rows = []
for idx, r in theory_df.iterrows():
    a = str(r['concept_a']).strip()
    b = str(r['concept_b']).strip()
    matched = False
    for pat in noise_pats:
        if pat.search(a) or pat.search(b):
            matched = True
            break
    if len(a.split()) > 10 or len(b.split()) > 10:
        matched = True
    if len(a) < 3 or len(b) < 3:
        matched = True
    if not matched:
        clean_rows.append((r['course_name'], a, b, r['label']))

print(f"Total clean rows: {len(clean_rows)}")
with open('scripts/clean_theory_rows_sample.txt', 'w', encoding='utf-8') as f:
    for course, a, b, lbl in clean_rows:
        f.write(f"[{course}] '{a}' -> '{b}' [label={lbl}]\n")

print("Wrote scripts/clean_theory_rows_sample.txt")

