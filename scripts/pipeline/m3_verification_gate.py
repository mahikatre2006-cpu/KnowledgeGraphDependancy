import sys, re, random, json
import pymupdf
import pandas as pd
from pathlib import Path

project_root = Path(r"c:\Users\Siddhesh\Documents\KnowledgeGraphDependancy")
pdf_dir = project_root / "DATA" / "raw" / "2019-scheme" / "Computer-Engineering"
extracted_dir = project_root / "DATA" / "extracted"
out_dir = project_root / "DATA" / "review" / "extraction_pages"
out_dir.mkdir(parents=True, exist_ok=True)

pdfs = [
    "be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf",
    "be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf",
    "be_computer-engineering_third-year-te-semester-5-rev-2019-c-scheme.pdf",
    "be_computer-engineering_third-year-te-semester-6-rev-2019-c-scheme.pdf",
    "be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf",
]

check_rows = []

for pdf_name in pdfs:
    print(f"\n--- Verifying {pdf_name} ---")
    with open(extracted_dir / f"{pdf_name}.json", "r", encoding="utf-8") as f:
        extracted = json.load(f)
        
    doc = pymupdf.open(str(pdf_dir / pdf_name))
    
    expected_codes = set()
    for page in doc:
        text = page.get_text()
        codes = re.findall(r'\b(CS[A-Z]\d{3}|CB[A-Z]\d{3})\b', text)
        expected_codes.update(codes)
        
    extracted_codes = {c['course_code'] for c in extracted}
    missing_codes = expected_codes - extracted_codes
    
    # 1. Subjects, topics, ratio
    print(f"Subjects extracted: {len(extracted)}")
    for c in extracted:
        t_count = len(c['topics'])
        flag = " ***[FLAG: out of bounds]***" if (t_count < 8 or t_count > 80) else ""
        print(f"  - {c['course_code']}: {t_count} topics{flag}")
        
    # 2. Cross-check
    print(f"\nExpected codes found in text: {len(expected_codes)}")
    print(f"Missing codes (not extracted): {sorted(missing_codes)}")
    
    # 3. Random sample 3 pages
    random.seed(42)
    valid_pages = [i for i in range(len(doc)) if len(doc[i].get_text("text").strip()) > 50]
    sample_pages = random.sample(valid_pages, min(3, len(valid_pages)))
    
    for pg_num in sample_pages:
        page = doc[pg_num]
        
        pix = page.get_pixmap(dpi=150)
        img_path = out_dir / f"{pdf_name}_page_{pg_num}.png"
        pix.save(str(img_path))
        
        text = page.get_text("text").replace('\n', ' ')
        found_topics = []
        for c in extracted:
            for t in c['topics']:
                # fuzzy match first 20 chars
                t_clean = t.replace('\n', ' ').strip()
                if t_clean[:20] in text:
                    found_topics.append(t_clean)
                    
        check_rows.append({
            "pdf": pdf_name,
            "page": pg_num,
            "extracted_topics": " | ".join(found_topics),
            "human_ok": ""
        })

df = pd.DataFrame(check_rows)
csv_path = project_root / "DATA" / "review" / "extraction_check.csv"
csv_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(csv_path, index=False)
print(f"\n✅ Step C: Verification samples written to {csv_path}")

