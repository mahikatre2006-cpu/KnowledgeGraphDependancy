import sys
import re
import json
import pymupdf
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

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
        if m.group(2): return [int(m.group(1)), int(m.group(2))]
        return [int(m.group(1))]
    return []

def get_semester_from_code(code):
    m = re.search(r'^[a-zA-Z]+(\d)', code)
    return int(m.group(1)) if m else None

from scripts.pipeline.audit_dataset import (
    check_person_name, check_publisher_citation, check_admin_rubric, 
    check_length_bound
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
                data.append({"pdf": pdf, "course": course, "json_path": json_path})
                for t in course.get("topics", []):
                    all_topics.append({"pdf": pdf, "code": course["course_code"], "topic": t})

print("=== 1. For checks 3 and 7 ===")
# Check 3
pub_words = r'\b(?:Wiley|PHI|TMH|Pearson|McGraw Hill|Cengage|Springer|Elsevier|Oxford University Press|Oracle Press|Prentice Hall|Addison Wesley)\b'
print(f"Check 3 - Reference leakage:")
print(f"  Number of topics scanned: {len(all_topics)}")
print(f"  Patterns used:")
print(f"    - ISBN: 'ISBN' in txt")
print(f"    - Year: r'\\b(?:19|20)\\d{{2}}\\b'")
print(f"    - Edition: r'\\bedition\\b' (ignore case)")
print(f"    - Publication: r'\\bpublication\\b' (ignore case)")
print(f"    - Publisher: r'{pub_words}' (ignore case)")
print(f"    - Author: r'\\b[A-Z]\\.\\s*[A-Z][a-z]+' or 'Herbert Schildt' in txt")

# Check 7
print(f"\nCheck 7 - Missing theory courses:")
for pdf in pdfs:
    pdf_path = pdf_dir / pdf
    doc = pymupdf.open(str(pdf_path))
    expected = set()
    for i, page in enumerate(doc):
        for match in re.finditer(r'(CS[A-Z]\d{3}|CB[A-Z]\d{3})\s*(.+)', page.get_text()):
            code = match.group(1).strip()
            if code.startswith("CSC") or code.startswith("CSDC") or code.startswith("CBC"):
                if not ("L" in code or "P" in code or "M" in code or "ILO" in code):
                    expected.add(code)
    extracted = set(d["course"]["course_code"] for d in data if d["pdf"] == pdf and (d["course"]["course_code"].startswith("CSC") or d["course"]["course_code"].startswith("CSDC")))
    print(f"  PDF: {pdf}")
    print(f"    Expected:  {sorted(list(expected))}")
    print(f"    Extracted: {sorted(list(extracted))}")


print("\n=== 2. For check 8 ===")
try:
    it_pdf_dir = project_root / "DATA" / "raw" / "2019-scheme" / "Information-Technology"
    it_pdfs = list(it_pdf_dir.glob("*.pdf"))
    it_course_topics = []
    for pdf_path in it_pdfs:
        blocks = extract_course_blocks_from_pdf(pdf_path)
        for code, name, topics in blocks:
            it_course_topics.append(len(topics))
                
    comps_course_topics = [len(d["course"].get("topics", [])) for d in data]
    
    print("COMPS topics per subject:")
    print(f"  min={np.min(comps_course_topics)}, p25={np.percentile(comps_course_topics, 25)}, median={np.median(comps_course_topics)}, p75={np.percentile(comps_course_topics, 75)}, max={np.max(comps_course_topics)}")
    print("IT topics per subject:")
    print(f"  min={np.min(it_course_topics)}, p25={np.percentile(it_course_topics, 25)}, median={np.median(it_course_topics)}, p75={np.percentile(it_course_topics, 75)}, max={np.max(it_course_topics)}")
    print(f"\nIT PDFs processed:")
    for p in it_pdfs: print(f"  - {p.name}")
    print(f"\nFile path each COMPS number was read from:")
    # Group by file path
    path_to_topics = defaultdict(list)
    for d in data:
        path_to_topics[str(d["json_path"])].append(len(d["course"].get("topics", [])))
    for p, counts in path_to_topics.items():
        print(f"  - {p}: {counts}")
except Exception as e:
    print(f"Error in Check 8: {e}")

print("\n=== 3. For check 4 ===")
tech_words = ["tree", "network", "memory", "algorithm", "protocol", "logic", "graph", "learning", "security", "python", "variable"]
tech_pattern = re.compile(r'\b(?:' + '|'.join(tech_words) + r')\b', re.I)

dropped_grouped = defaultdict(list)
for pdf in pdfs:
    raw_courses = custom_comps_extractor(pdf_dir / pdf)
    for code, name, topics in raw_courses:
        for t in topics:
            reason = []
            if check_person_name(t): reason.append("Author")
            if check_publisher_citation(t): reason.append("Publisher")
            if check_admin_rubric(t): reason.append("Admin")
            if check_length_bound(t): reason.append("Length")
            
            if reason and tech_pattern.search(t):
                # Is it legitimate reference or wrongly removed?
                # Simple heuristic: if it contains "Press" or "Pearson" it's likely a reference. But wait, we want to label it manually or apply a heuristic.
                # Actually, I'll print them all and the user can see.
                dropped_grouped["+".join(reason)].append(f"{code}: {t}")

for group, items in dropped_grouped.items():
    print(f"\nFilter: {group} (Total: {len(items)})")
    for item in items:
        # Determine if it's legit reference or wrongly removed
        is_ref = "Legitimate reference" if re.search(r'\b(?:Edition|ISBN|Press|Pearson|PHI|McGraw Hill|Wiley|Springer)\b', item, re.I) else "Wrongly removed (technical topic)"
        print(f"  - [{is_ref}] {item}")

print("\n=== 4. For check 9 ===")
check_csv = project_root / "DATA" / "review" / "extraction_check.csv"
targ_csv = project_root / "DATA" / "review" / "extraction_targeted.csv"
try:
    df_check = pd.read_csv(check_csv)
    print("extraction_check.csv loaded successfully.")
except Exception as e:
    print(f"extraction_check.csv failed: {e}")

try:
    df_targ = pd.read_csv(targ_csv)
    print("extraction_targeted.csv loaded successfully.")
except Exception as e:
    print(f"extraction_targeted.csv failed: {e}")

print("\n=== 5. For checks 1, 2, 5, 6 (Full Lists) ===")
# Check 1
code_to_pdfs = defaultdict(set)
for d in data: code_to_pdfs[d["course"]["course_code"]].add(d["pdf"])
duplicates_across_pdfs = [c for c, p in code_to_pdfs.items() if len(p) > 1]
semester_mismatches = []
for d in data:
    code = d["course"]["course_code"]
    pdf = d["pdf"]
    expected_sems = get_semester_from_pdf(pdf)
    actual_sem = get_semester_from_code(code)
    if actual_sem is not None and actual_sem not in expected_sems:
        semester_mismatches.append(f"{code} in {pdf}")

print(f"\n[Check 1] Duplicates across PDFs ({len(duplicates_across_pdfs)}):")
for x in duplicates_across_pdfs: print(f"  - {x} is in PDFs: {list(code_to_pdfs[x])}")
print(f"\n[Check 1] Semester mismatches ({len(semester_mismatches)}):")
for x in semester_mismatches: print(f"  - {x}")

# Check 2
empty_tiny = []
for d in data:
    t_count = len(d["course"].get("topics", []))
    if t_count < 8:
        code = d["course"]["course_code"]
        cls = "lab/project" if "L" in code or "P" in code or "M" in code else "header-only/extraction miss"
        if t_count == 0: cls = "0-topics " + cls
        empty_tiny.append(f"{code} ({t_count} topics) [{cls}]")
print(f"\n[Check 2] Empty or tiny subjects ({len(empty_tiny)}):")
for x in empty_tiny: print(f"  - {x}")

# Check 5
malformed = []
for t in all_topics:
    txt = t["topic"]
    if len(txt) > 100:
        malformed.append(f"[>100 chars] {t['code']}: {txt[:80]}...")
    elif re.search(r'\s[A-Z]\.\s', txt) or re.search(r'\d+\.\d+', txt):
        malformed.append(f"[Numbering] {t['code']}: {txt}")
    elif re.search(r'\b(?:Course Code|Course Name|Credit|Teaching Scheme|Examination Scheme|Marks)\b', txt, re.I):
        malformed.append(f"[Table header] {t['code']}: {txt}")
    elif len(txt.split()) == 1 and txt.strip().endswith((',', '.')):
        malformed.append(f"[Fragment] {t['code']}: {txt}")

print(f"\n[Check 5] Merged/malformed topics ({len(malformed)}):")
for x in malformed: print(f"  - {x}")

# Check 6
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
                if len(span_pages) > 3: break
        codes_in_span = list(set(codes_in_span) - {d["course"]["course_code"]})
        sem78.append(f"{d['course']['course_code']} has {t_count} topics. Found codes in span: {codes_in_span}")
print(f"\n[Check 6] Sem 7-8 boundaries ({len(sem78)}):")
for x in sem78: print(f"  - {x}")

