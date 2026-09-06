import pandas as pd

df = pd.read_csv('Cleaned_Files/labeling_dataset_cleaned.csv')
with open('scripts/inspect_cleaned_dataset_by_course.txt', 'w', encoding='utf-8') as f:
    for course, group in df.groupby('course_name'):
        f.write(f"\n=======================================================\n")
        f.write(f"COURSE: {course} ({len(group)} rows, pos: {(group['label']==1).sum()}, neg: {(group['label']==0).sum()})\n")
        f.write(f"=======================================================\n")
        for i, r in group.head(10).iterrows():
            f.write(f"  [{r['label']}] '{r['concept_a']}' -> '{r['concept_b']}'\n")

print("Wrote scripts/inspect_cleaned_dataset_by_course.txt")

