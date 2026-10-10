import sys
import re
import json
import random
import pymupdf
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

random.seed(42)

project_root = Path(r"c:\Users\Siddhesh\Documents\KnowledgeGraphDependancy")
sys.path.insert(0, str(project_root))
pdf_dir = project_root / "DATA" / "raw" / "2019-scheme" / "Computer-Engineering"
extracted_dir = project_root / "DATA" / "extracted"

pdfs = [
    "be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf",
    "be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf",
    "be_computer-engineering_third-year-te-semester-5-rev-2019-c-scheme.pdf",
    "be_computer-engineering_third-year-te-semester-6-rev-2019-c-scheme.pdf",
    "be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf",
]

def get_semester_from_pdf(pdf_name):
    m = re.search(r'semester-(\d+)(?:-(\d+))?', pdf_name)
    if m:
        if m.group(2):
            return [int(m.group(1)), int(m.group(2))]
        return [int(m.group(1))]
    return []

def get_semester_from_code(code):
    m = re.search(r'^[a-zA-Z]+(\d)', code)
    if m:
        return int(m.group(1))
    return None

from scripts.pipeline.audit_dataset import (
    check_person_name, check_publisher_citation, check_admin_rubric, 
    check_tool_fragment, check_length_bound, check_truncated_fragment
)
from scripts.pipeline.m3_diagnose_and_extract import custom_comps_extractor
from scripts.pipeline.full_pipeline import extract_course_blocks_from_pdf

data = []
all_topics = []
for pdf in pdfs:
    json_path = extracted_dir / (pdf + ".json")
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            pdf_data = json.load(f)
            for course in pdf_data:
                data.append({"pdf": pdf, "course": course})
                for t in course.get("topics", []):
                    all_topics.append({"pdf": pdf, "code": course["course_code"], "topic": t})

results = []
print("=== Phase 1 Audit ===")

# Check 1: Duplicate subjects
code_to_pdfs = defaultdict(set)
for d in data:
    code_to_pdfs[d["course"]["course_code"]].add(d["pdf"])
duplicates_across_pdfs = [c for c, p in code_to_pdfs.items() if len(p) > 1]
semester_mismatches = []
for d in data:
    code = d["course"]["course_code"]
    pdf = d["pdf"]
    expected_sems = get_semester_from_pdf(pdf)
    actual_sem = get_semester_from_code(code)
    if actual_sem is not None and actual_sem not in expected_sems:
        semester_mismatches.append(f"{code} in {pdf}")

c1_fails = len(duplicates_across_pdfs) + len(semester_mismatches)
status1 = "FAIL" if c1_fails > 0 else "PASS"
results.append(("1. Duplicate subjects", status1, c1_fails))
print(f"\n[1] Duplicate subjects: {status1} ({c1_fails})")
if duplicates_across_pdfs:
    print("  Course codes in >1 PDF:")
    for x in random.sample(duplicates_across_pdfs, min(10, len(duplicates_across_pdfs))): print(f"    - {x}")
if semester_mismatches:
    print("  Semester mismatches:")
    for x in random.sample(semester_mismatches, min(10, len(semester_mismatches))): print(f"    - {x}")

# Check 2: Empty or tiny subjects
empty_tiny = []
for d in data:
    t_count = len(d["course"].get("topics", []))
    if t_count < 8:
        code = d["course"]["course_code"]
        cls = "lab/project" if "L" in code or "P" in code or "M" in code else "header-only/extraction miss"
        if t_count == 0:
            cls = "0-topics " + cls
        empty_tiny.append(f"{code} ({t_count} topics) [{cls}]")

status2 = "FAIL" if len(empty_tiny) > 0 else "PASS"
results.append(("2. Empty or tiny subjects", status2, len(empty_tiny)))
print(f"\n[2] Empty or tiny subjects: {status2} ({len(empty_tiny)})")
if empty_tiny:
    for x in random.sample(empty_tiny, min(10, len(empty_tiny))): print(f"  - {x}")

# Check 3: Reference leakage
ref_leaks = []
pub_words = r'\b(?:Wiley|PHI|TMH|Pearson|McGraw Hill|Cengage|Springer|Elsevier|Oxford University Press|Oracle Press|Prentice Hall|Addison Wesley)\b'
for t in all_topics:
    txt = t["topic"]
    leak = None
    if "ISBN" in txt: leak = "ISBN"
    elif re.search(r'\b(?:19|20)\d{2}\b', txt): leak = "Year"
    elif re.search(r'\bedition\b', txt, re.I): leak = "Edition"
    elif re.search(r'\bpublication\b', txt, re.I): leak = "Publication"
    elif re.search(pub_words, txt, re.I): leak = "Publisher"
    elif re.search(r'\b[A-Z]\.\s*[A-Z][a-z]+', txt) or "Herbert Schildt" in txt: leak = "Author"
    
    # Also check if text is after "Text Books" or "References" heading
    
    if leak:
        ref_leaks.append(f"[{leak}] {t['code']}: {txt}")

status3 = "FAIL" if len(ref_leaks) > 0 else "PASS"
results.append(("3. Reference leakage", status3, len(ref_leaks)))
print(f"\n[3] Reference leakage: {status3} ({len(ref_leaks)})")
if ref_leaks:
    for x in random.sample(ref_leaks, min(10, len(ref_leaks))): print(f"  - {x}")

# Check 4: Over-dropping
dropped_topics = []
tech_words = ["tree", "network", "memory", "algorithm", "protocol", "logic", "graph", "learning", "security", "python", "variable"]
tech_pattern = re.compile(r'\b(?:' + '|'.join(tech_words) + r')\b', re.I)
for pdf in pdfs:
    pdf_path = pdf_dir / pdf
    raw_courses = custom_comps_extractor(pdf_path)
    for code, name, topics in raw_courses:
        for t in topics:
            if (check_person_name(t) or check_publisher_citation(t) or check_admin_rubric(t) or check_length_bound(t)):
                if tech_pattern.search(t):
                    reason = []
                    if check_person_name(t): reason.append("Author")
                    if check_publisher_citation(t): reason.append("Publisher")
                    if check_admin_rubric(t): reason.append("Admin")
                    if check_length_bound(t): reason.append("Length")
                    dropped_topics.append(f"[{'+'.join(reason)}] {code}: {t}")

status4 = "FAIL" if len(dropped_topics) > 0 else "PASS"
results.append(("4. Over-dropping", status4, len(dropped_topics)))
print(f"\n[4] Over-dropping: {status4} ({len(dropped_topics)})")
if dropped_topics:
    for x in random.sample(dropped_topics, min(10, len(dropped_topics))): print(f"  - {x}")

# Check 5: Merged/malformed topics
malformed = []
for t in all_topics:
    txt = t["topic"]
    if len(txt) > 100:
        malformed.append(f"[>100 chars] {t['code']}: {txt[:60]}...")
    elif re.search(r'\s[A-Z]\.\s', txt) or re.search(r'\d+\.\d+', txt):
        malformed.append(f"[Numbering] {t['code']}: {txt}")
    elif re.search(r'\b(?:Course Code|Course Name|Credit|Teaching Scheme|Examination Scheme|Marks)\b', txt, re.I):
        malformed.append(f"[Table header] {t['code']}: {txt}")
    elif len(txt.split()) == 1 and txt.strip().endswith((',', '.')):
        malformed.append(f"[Fragment] {t['code']}: {txt}")

status5 = "FAIL" if len(malformed) > 0 else "PASS"
results.append(("5. Merged/malformed topics", status5, len(malformed)))
print(f"\n[5] Merged/malformed topics: {status5} ({len(malformed)})")
if malformed:
    for x in random.sample(malformed, min(10, len(malformed))): print(f"  - {x}")

# Check 6: Sem 7-8 boundaries
sem78 = []
for d in data:
    t_count = len(d["course"].get("topics", []))
    if t_count > 80:
        pdf_path = pdf_dir / d["pdf"]
        doc = pymupdf.open(str(pdf_path))
        codes_in_span = []
        found_code = False
        span_pages = []
        for i, page in enumerate(doc):
            text = page.get_text()
            if d["course"]["course_code"] in text:
                found_code = True
            if found_code:
                span_pages.append(i)
                codes = re.findall(r'(CS[A-Z]\d{3})', text)
                codes_in_span.extend(codes)
                if len(span_pages) > 3:
                    break
        codes_in_span = list(set(codes_in_span) - {d["course"]["course_code"]})
        sem78.append(f"{d['course']['course_code']} has {t_count} topics. Found codes in span: {codes_in_span}")

status6 = "FAIL" if len(sem78) > 0 else "PASS"
results.append(("6. Sem 7-8 boundaries", status6, len(sem78)))
print(f"\n[6] Sem 7-8 boundaries: {status6} ({len(sem78)})")
if sem78:
    for x in sem78: print(f"  - {x}")

# Check 7: Missing theory courses
missing_theory = []
theory_extracted = set(d["course"]["course_code"] for d in data if d["course"]["course_code"].startswith("CSC") or d["course"]["course_code"].startswith("CSDC"))
expected_theory = set()
for pdf in pdfs:
    pdf_path = pdf_dir / pdf
    doc = pymupdf.open(str(pdf_path))
    for i, page in enumerate(doc):
        text = page.get_text()
        matches = re.finditer(r'(CS[A-Z]\d{3}|CB[A-Z]\d{3})\s*(.+)', text)
        for match in matches:
            code = match.group(1).strip()
            if code.startswith("CSC") or code.startswith("CSDC") or code.startswith("CBC"):
                if not ("L" in code or "P" in code or "M" in code or "ILO" in code):
                    expected_theory.add(code)

missing_codes = expected_theory - theory_extracted
if missing_codes:
    for c in missing_codes:
        missing_theory.append(c)

status7 = "FAIL" if len(missing_theory) > 0 else "PASS"
results.append(("7. Missing theory courses", status7, len(missing_theory)))
print(f"\n[7] Missing theory courses: {status7} ({len(missing_theory)})")
if missing_theory:
    print(f"  Missing theory codes: {missing_theory}")

# Check 8: Granularity
print("\n[8] Granularity:")
try:
    rebuild_dir = project_root / "DATA" / "rebuild_check"
    rebuild_dir.mkdir(parents=True, exist_ok=True)
    it_pdf_dir = project_root / "DATA" / "raw" / "2019-scheme" / "Information-Technology"
    it_pdfs = list(it_pdf_dir.glob("*.pdf"))
    
    it_course_topics = []
    print(f"  Extracting {len(it_pdfs)} IT PDFs via full_pipeline.extract_course_blocks_from_pdf...")
    for pdf_path in it_pdfs:
        blocks = extract_course_blocks_from_pdf(pdf_path)
        for code, name, topics in blocks:
            it_course_topics.append(len(topics))
                
    comps_course_topics = [len(d["course"].get("topics", [])) for d in data]
    
    if len(comps_course_topics) > 0:
        print(f"  COMPS topics/subject: min={np.min(comps_course_topics)}, median={np.median(comps_course_topics)}, max={np.max(comps_course_topics)}")
    else:
        print("  COMPS topics/subject: no courses found")
        
    if len(it_course_topics) > 0:
        print(f"  IT topics/subject: min={np.min(it_course_topics)}, median={np.median(it_course_topics)}, max={np.max(it_course_topics)}")
    else:
        print("  IT topics/subject: no courses found")
        
    results.append(("8. Granularity", "INFO", 0))
except Exception as e:
    print(f"  Error in Granularity check: {e}")
    results.append(("8. Granularity", "ERROR", 0))

# Check 9: Review files
check_csv = project_root / "DATA" / "review" / "extraction_check.csv"
targ_csv = project_root / "DATA" / "review" / "extraction_targeted.csv"
c9_fails = 0
c9_msgs = []
try:
    df_check = pd.read_csv(check_csv)
    if df_check.empty: 
        c9_fails += 1
        c9_msgs.append("extraction_check.csv is empty")
    else:
        # Check if topics are really on the page
        fail_topics = []
        for idx, row in df_check.iterrows():
            pdf_path = pdf_dir / row["PDF_Name"]
            page_idx = int(row["Page_Number"])
            topics = eval(row["Topics"]) if isinstance(row["Topics"], str) else []
            doc = pymupdf.open(str(pdf_path))
            # page_idx in csv is usually 0-indexed or 1-indexed. Let's assume 0-indexed if possible.
            # usually human readable is 1-indexed, we'll check both.
            page_text = doc[page_idx-1].get_text().replace('\n', ' ') if page_idx > 0 else doc[page_idx].get_text().replace('\n', ' ')
            page_text2 = doc[page_idx].get_text().replace('\n', ' ') if page_idx < len(doc) else ""
            
            # just check if the first topic text snippet is roughly found
            for t in topics:
                # simplify spaces
                t_clean = re.sub(r'\s+', ' ', t).strip()[:20]
                if t_clean not in page_text and t_clean not in page_text2:
                    fail_topics.append(f"{row['Course_Code']} topic not on page {page_idx}")
                    break
        if fail_topics:
            c9_fails += len(fail_topics)
            c9_msgs.append(f"{len(fail_topics)} topics not found on designated pages")
except Exception as e:
    c9_fails += 1
    c9_msgs.append(f"extraction_check.csv read error: {e}")

try:
    df_targ = pd.read_csv(targ_csv)
    if df_targ.empty: 
        c9_fails += 1
        c9_msgs.append("extraction_targeted.csv is empty")
except Exception as e:
    c9_fails += 1
    c9_msgs.append(f"extraction_targeted.csv read error: {e}")

status9 = "FAIL" if c9_fails > 0 else "PASS"
results.append(("9. Review files", status9, c9_fails))
print(f"\n[9] Review files: {status9} ({c9_fails})")
for m in c9_msgs:
    print(f"  - {m}")

print("\n=== SUMMARY ===")
for check, status, count in results:
    print(f"{check:30} | {status:6} | {count}")

