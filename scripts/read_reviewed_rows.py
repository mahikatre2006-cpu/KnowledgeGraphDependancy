import pandas as pd

df = pd.read_csv("DATA/review/extraction_pilot_reviewed.csv")

target_topics = [
    ("ITC501", "Document Object Model"),
    ("ITC501", "Promises and Fetch API"),
    ("ITC501", "React Forms and Events"),
    ("ITC501", "Flux Architecture"),
    ("ITC501", "Node.js File System"),
    ("ITC501", "Node.js Web Module"),
    ("ITC501", "REST API in Express"),
    ("ITC501", "Express Generator"),
    ("CSC303", "Concept of Abstract Data Types")
]

print("=== Reading human_ok and human_note from extraction_pilot_reviewed.csv ===")
for code, name in target_topics:
    row = df[(df["course_code"].astype(str) == code) & (df["topic_name"] == name)]
    if not row.empty:
        r = row.iloc[0]
        h_ok = r.get("human_ok")
        h_note = r.get("human_note")
        h_note_str = f"'{h_note}'" if pd.notna(h_note) and str(h_note).strip() else "(empty)"
        print(f"[{code}] {name:<32} | human_ok: {h_ok} | human_note: {h_note_str}")
    else:
        print(f"[{code}] {name:<32} | NOT FOUND")

