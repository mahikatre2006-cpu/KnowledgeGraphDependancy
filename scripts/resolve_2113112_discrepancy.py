import json
import re
import fitz
import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load the PDF text for 2113112 (pages 19, 20, 21)
pdf_path = "DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf"
doc = fitz.open(pdf_path)
pages = {p: doc[p-1].get_text("text") for p in [19, 20, 21]}

def normalize_text_for_match(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    t = t.replace('\u2013', '-').replace('\u2014', '-').replace('\u2015', '-')
    t = t.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    t = re.sub(r'\s+', ' ', t)
    return t.strip().lower()

norm_pages = {p: normalize_text_for_match(txt) for p, txt in pages.items()}

def validate(topics):
    accepted = []
    rejected = []
    seen = set()
    banned = ['mark', 'marks', 'credit', 'credits', 'hour', 'hours', 'textbook', 'reference', 'syllabus', 'assessment', 'prerequisite']
    for t in topics:
        name = t.get("name", "").strip()
        quote = t.get("source_quote", "").strip()
        unit = t.get("unit", "").strip()
        page = t.get("page")
        words = name.split()
        norm_name = normalize_text_for_match(name)
        norm_quote = normalize_text_for_match(quote)
        if not quote:
            rejected.append((t, "empty quote"))
            continue
        if len(quote) > 200:
            rejected.append((t, f"quote > 200 ({len(quote)})"))
            continue
        matched_page = None
        if page in norm_pages and norm_quote in norm_pages[page]:
            matched_page = page
        else:
            for p, p_text in norm_pages.items():
                if norm_quote in p_text:
                    matched_page = p
                    break
        if not matched_page:
            rejected.append((t, f"quote not on page {page}"))
            continue
        if len(words) < 1 or len(words) > 8:
            rejected.append((t, f"word count {len(words)}"))
            continue
        if norm_name in seen:
            rejected.append((t, f"duplicate: {name}"))
            continue
        if any(re.search(r'\b' + re.escape(b) + r'\b', norm_name) for b in banned):
            rejected.append((t, "banned word"))
            continue
        seen.add(norm_name)
        accepted.append(t)
    return accepted, rejected

with open("DATA/processed/gemini_cache/257ca70b7c2c58a2070c025a92525688482177de66531f034f4e3bb2ba5d4c74.json", "r", encoding="utf-8") as f:
    f_orig = json.load(f)

with open("DATA/processed/gemini_cache/2113112_rerun.json", "r", encoding="utf-8") as f:
    f_rerun = json.load(f)

with open("DATA/processed/gemini_cache/2113112_v2.json", "r", encoding="utf-8") as f:
    f_v2 = json.load(f)

print("=== 1. Original Hash Cache (257ca7...): ===")
print("Raw count:", len(f_orig["topics"]))
acc_orig, rej_orig = validate(f_orig["topics"])
print("Accepted count:", len(acc_orig))
print("Rejected count:", len(rej_orig))
for r_t, r_reason in rej_orig:
    print(f"  Rejected: '{r_t['name']}': {r_reason}")

print("\n=== 2. 2113112_rerun.json Cache: ===")
print("Raw count:", len(f_rerun["topics"]))
acc_rerun, rej_rerun = validate(f_rerun["topics"])
print("Accepted count:", len(acc_rerun))
print("Rejected count:", len(rej_rerun))
for r_t, r_reason in rej_rerun:
    print(f"  Rejected: '{r_t['name']}': {r_reason}")

print("\n=== 3. 2113112_v2.json Cache: ===")
print("Raw count:", len(f_v2["topics"]))
acc_v2, rej_v2 = validate(f_v2["topics"])
print("Accepted count:", len(acc_v2))
print("Rejected count:", len(rej_v2))
for r_t, r_reason in rej_v2:
    print(f"  Rejected: '{r_t['name']}': {r_reason}")

print("\n=== Check extraction_pilot_reviewed.csv topics for 2113112: ===")
df_rev = pd.read_csv("DATA/review/extraction_pilot_reviewed.csv")
rev_2113112 = df_rev[df_rev["course_code"].astype(str) == "2113112"]
print("\n=== Check Rings in 257ca7... ===")
rings_topic = [t for t in f_orig["topics"] if t["name"] == "Rings"][0]
print("Rings topic record:", rings_topic)

# Check why it was rejected by run_stage_b_pilot.py
norm_q = normalize_text_for_match(rings_topic["source_quote"])
print("Normalized quote:", repr(norm_q))
p = rings_topic["page"]
print(f"Page reported: {p}")
print(f"Is norm_q in page {p}?", norm_q in norm_pages.get(p, ""))
for p_num, p_txt in norm_pages.items():
    print(f"Is norm_q in page {p_num}?", norm_q in p_txt)
