import json
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, 'scripts')
import fitz
from run_stage_b_pilot import validate_topics, extract_pdf_page_texts

with open("DATA/processed/gemini_cache/257ca70b7c2c58a2070c025a92525688482177de66531f034f4e3bb2ba5d4c74.json", "r", encoding="utf-8") as f:
    orig_data = json.load(f)

pdf_pages = extract_pdf_page_texts("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf", [19, 20, 21])

acc, rej = validate_topics(orig_data["topics"], pdf_pages)
print("Raw topics in 257ca7...:", len(orig_data["topics"]))
print("Accepted count via run_stage_b_pilot:", len(acc))
print("Rejected count via run_stage_b_pilot:", len(rej))
for t, r in rej:
    print(f"  Rejected: '{t['name']}': {r}")

df_rev = pd.read_csv("DATA/review/extraction_pilot_reviewed.csv")
rev_2113112 = df_rev[df_rev["course_code"].astype(str) == "2113112"]
print("\nReviewed CSV rows for 2113112:", len(rev_2113112))

acc_names = [t["name"] for t in acc]
rev_names = rev_2113112["topic_name"].tolist()
print("Matches reviewed rows exactly?:", acc_names == rev_names)
