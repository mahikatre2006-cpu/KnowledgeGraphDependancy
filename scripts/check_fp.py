import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from scripts.audit_dataset import check_person_name, evaluate_concept

df = pd.read_csv('Cleaned_Files/labeling_dataset.csv')

false_positive_concepts = {
    'Block Ciphers', 'Digital Certificates', 'Modular Arithmetic',
    'Normal Distribution', 'Poisson Distribution', 'Regular Expression',
    'Regular Language', 'Sliding Window', 'Spring Boot', 'Time Division',
    'Convergence Speed', 'Search Techniques', 'Statistical Techniques',
    'Text Processing', 'User Experience', 'Object Oriented', 'Technology Stack'
}

affected_rows = []
for idx, row in df.iterrows():
    a = row['concept_a']
    b = row['concept_b']
    if a in false_positive_concepts or b in false_positive_concepts:
        reasons_a = evaluate_concept(a)
        reasons_b = evaluate_concept(b)
        affected_rows.append((idx, a, b, reasons_a, reasons_b, row['label']))

print(f"Total rows involving these legitimate concepts: {len(affected_rows)}")
# How many of these rows were flagged ONLY because of these legitimate concepts?
rescued = 0
for idx, a, b, ra, rb, lbl in affected_rows:
    # If a is in false_positive_concepts and flagged person_name, but has no other flaw
    a_flawed = [r for r in ra if not (r == 'person_name' and a in false_positive_concepts)]
    b_flawed = [r for r in rb if not (r == 'person_name' and b in false_positive_concepts)]
    if not a_flawed and not b_flawed:
        rescued += 1

print(f"Rows that are completely clean and were mistakenly flagged: {rescued}")
