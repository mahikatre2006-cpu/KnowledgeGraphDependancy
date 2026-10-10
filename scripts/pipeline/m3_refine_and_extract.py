import sys, re, json, random
import pymupdf
import numpy as np
import pandas as pd
from pathlib import Path

project_root = Path(r"c:\Users\Siddhesh\Documents\KnowledgeGraphDependancy")
sys.path.insert(0, str(project_root))

from scripts.pipeline.audit_dataset import (
    check_person_name, check_publisher_citation, check_admin_rubric, 
    check_tool_fragment, check_truncated_fragment
)
from scripts.pipeline.full_pipeline import build_candidate_pairs

def clean_and_split_topics(raw_text):
    """
    Granularity rule: Split raw module text by newlines and commas.
    Keep segments > 5 characters that are not noise.
    Matches the IT pipeline's median granularity (~3 topics per subject).
    """
    topics = []
    # Split by newline or comma
    segments = re.split(r'[\n,]', raw_text)
    for seg in segments:
        seg = seg.strip()
        # Remove leading numbers like "1.1", "i.", etc.
        seg = re.sub(r'^(\d+\.\d+|\d+\.|[ivx]+\.)\s*', '', seg, flags=re.I)
        seg = seg.strip()
        
        if len(seg) > 5:
            # Apply standard contamination filters
            if not (check_person_name(seg) or check_publisher_citation(seg) or 
                    check_admin_rubric(seg) or re.match(r'^Text\s*Books', seg, re.I) or 
                    re.match(r'^References', seg, re.I) or re.match(r'^Assessment', seg, re.I) or
                    "Self-learning" in seg or "Self Learning" in seg):
                
                # Check for pure noise
                if not re.fullmatch(r'[\d\s\-\.\,\(\)\*\+\/]+', seg):
                    topics.append(seg)
    return topics

def get_expected_codes(doc):
    """Finds all valid course codes in the PDF by scanning early pages."""
    codes = set()
    for i in range(min(15, len(doc))):
        text = doc[i].get_text()
        found = re.findall(r'\b(?:CS[A-Z]{0,2}|CB[A-Z]{0,2}|IL[A-Z]{0,2})\d{3,4}\b', text)
        codes.update(found)
    return codes

def extract_from_pdf(pdf_path):
    doc = pymupdf.open(str(pdf_path))
    expected_codes = get_expected_codes(doc)
    
    courses = {}
    current_code = None
    current_name = None
    current_raw_text = []
    
    for i, page in enumerate(doc):
        text = page.get_text("text")
        
        # Identify course boundaries using the exact codes found in the program structure
        # We look for a line that starts with the course code
        lines = text.split('\n')
        for j, line in enumerate(lines):
            line_str = line.strip()
            
            # Match course boundary (e.g. "CSC301  Engineering Mathematics-III")
            code_match = re.match(r'^((?:CS[A-Z]{0,2}|CB[A-Z]{0,2}|IL[A-Z]{0,2})\d{3,4})\b', line_str)
            if code_match:
                code = code_match.group(1)
                if code in expected_codes:
                    name_part = line_str[len(code):].strip()
                    if not name_part and j+1 < len(lines):
                        name_part = lines[j+1].strip()
                    
                    if len(name_part) > 3 and "Credits" not in name_part and "Course Name" not in name_part:
                        if current_code and current_code != code and current_raw_text:
                            courses[current_code] = (current_code, current_name, clean_and_split_topics("\n".join(current_raw_text)))
                        
                        if current_code != code:
                            current_code = code
                            current_name = name_part
                            current_raw_text = []
                            continue
                            
            # Accumulate module text
            if current_code:
                # Only accumulate lines that look like syllabus topics (e.g. 1.1 Topic)
                if re.match(r'^(\d+\.\d+|[ivx]+\.)', line_str) or current_raw_text:
                    if "Text Books" in line_str or "References" in line_str or "Assessment" in line_str or "Term Work" in line_str:
                        # End of syllabus for this course
                        courses[current_code] = (current_code, current_name, clean_and_split_topics("\n".join(current_raw_text)))
                        current_code = None
                        current_raw_text = []
                    elif line_str and not re.match(r'^\d+$', line_str): # skip pure digits (module numbers)
                        current_raw_text.append(line_str)
                        
    if current_code and current_raw_text:
        courses[current_code] = (current_code, current_name, clean_and_split_topics("\n".join(current_raw_text)))
        
    return courses, expected_codes, doc

def main():
    print("=== Step 1 & 3: Dedupe, Boundaries & Extraction ===")
    pdf_dir = project_root / "DATA" / "raw" / "2019-scheme" / "Computer-Engineering"
    pdfs = [
        ("sem-3", "be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf"),
        ("sem-4", "be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf"),
        ("sem-5", "be_computer-engineering_third-year-te-semester-5-rev-2019-c-scheme.pdf"),
        ("sem-6", "be_computer-engineering_third-year-te-semester-6-rev-2019-c-scheme.pdf"),
        ("sem-7-8", "be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf"),
    ]

    registry = {}
    duplicates_removed = []
    
    # Store docs for sample rendering later
    docs = {}
    missing_targets = []
    
    for sem_tag, pdf_name in pdfs:
        pdf_path = pdf_dir / pdf_name
        courses, expected_codes, doc = extract_from_pdf(pdf_path)
        docs[pdf_name] = doc
        
        # Step 4: Completeness Check
        theory_codes = {c for c in expected_codes if not re.match(r'^(CSL|CSP|CSM)', c)}
        extracted_theory = {c for c in courses.keys() if not re.match(r'^(CSL|CSP|CSM)', c)}
        missing = theory_codes - extracted_theory
        
        if missing:
            print(f"\n[{sem_tag}] Missing Theory/Elective Codes: {sorted(missing)}")
            for m_code in missing:
                # Find page
                for i, page in enumerate(doc):
                    if m_code in page.get_text():
                        missing_targets.append({"pdf": pdf_name, "page": i, "code": m_code, "text": page.get_text().splitlines()[:15]})
                        break
        
        # Step 1: Dedupe and register
        for code, (c, n, t) in courses.items():
            # Determine true semester from the code (e.g. CSC301 -> 3)
            match = re.search(r'\D(\d)\d{2,3}', code)
            true_sem = f"sem-{match.group(1)}" if match else sem_tag
            
            # Prefer the file that matches the true semester
            if code in registry:
                existing_sem = registry[code]['true_sem']
                existing_file = registry[code]['file']
                if sem_tag == true_sem and existing_sem != existing_file:
                    duplicates_removed.append(f"{code} (kept {pdf_name}, dropped {existing_file})")
                    registry[code] = {'file': pdf_name, 'true_sem': true_sem, 'course': (c, n, t)}
                else:
                    duplicates_removed.append(f"{code} (kept {existing_file}, dropped {pdf_name})")
            else:
                registry[code] = {'file': pdf_name, 'true_sem': true_sem, 'course': (c, n, t)}

    print(f"\nDuplicates removed: {len(duplicates_removed)}")
    for d in duplicates_removed[:5]:
        print("  -", d)
    if len(duplicates_removed) > 5:
        print(f"  ... and {len(duplicates_removed)-5} more")
        
    print("\n=== Step 4: Missing Code Diagnostics ===")
    for target in missing_targets:
        print(f"Missing: {target['code']} in {target['pdf']} (Page {target['page']})")
        print("First 15 lines:")
        for line in target['text']:
            print(" |", line.strip())
        print("-" * 40)

    # Compile final list
    final_courses = [v['course'] for v in registry.values()]
    all_courses_tagged = []
    for code, v in registry.items():
        all_courses_tagged.append((v['file'], v['course'][0], v['course'][1], v['course'][2]))
        
    # Step 2: Topic Granularity Reporting
    comps_counts = [len(t) for _, _, t in final_courses]
    print("\n=== Step 2 & 6: Final Stats ===")
    print(f"Final subjects extracted: {len(final_courses)}")
    print(f"Topics per COMPS subject (new rule): min={np.min(comps_counts)}, median={np.median(comps_counts)}, max={np.max(comps_counts)}")
    print("Exact rule used for topic units: Split raw module content by newlines and commas, yielding distinct topic strings > 5 chars, omitting numbers and noise, matching the IT pipeline's median granularity.")
    
    # Write extraction outputs for pair generation
    out_csv = project_root / "DATA" / "candidates" / "mu_comp_eng_new_pairs.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_new = build_candidate_pairs(all_courses_tagged)
    df_new.to_csv(out_csv, index=False)
    
    # Step 5: Review Files
    print("\n=== Step 5: Review Files ===")
    out_dir = project_root / "DATA" / "review" / "extraction_pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    check_rows = []
    targeted_rows = []
    
    random.seed(42)
    for pdf_name in [p[1] for p in pdfs]:
        doc = docs[pdf_name]
        valid_pages = [i for i in range(len(doc)) if len(doc[i].get_text("text").strip()) > 50]
        sample_pages = random.sample(valid_pages, min(3, len(valid_pages)))
        
        pdf_courses = [v['course'] for v in registry.values() if v['file'] == pdf_name]
        
        for pg_num in sample_pages:
            page = doc[pg_num]
            pix = page.get_pixmap(dpi=150)
            pix.save(str(out_dir / f"{pdf_name}_page_{pg_num}.png"))
            
            text = page.get_text("text").replace('\n', ' ')
            found_topics = []
            for c, n, tops in pdf_courses:
                for t in tops:
                    if t[:20] in text:
                        found_topics.append(t)
            check_rows.append({
                "pdf": pdf_name,
                "page": pg_num,
                "extracted_topics": " | ".join(found_topics),
                "human_ok": ""
            })

    # Add targeted rows for subjects < 8 topics to verify new granularity
    targeted_subjects = [c for c in final_courses if len(c[2]) < 8]
    for c, n, tops in targeted_subjects:
        # find the pdf and page
        pdf_name = registry[c]['file']
        doc = docs[pdf_name]
        found_pg = 0
        for i, page in enumerate(doc):
            if c in page.get_text():
                found_pg = i
                break
        
        page = doc[found_pg]
        pix = page.get_pixmap(dpi=150)
        pix.save(str(out_dir / f"TARGETED_{c}_{pdf_name}_page_{found_pg}.png"))
        
        targeted_rows.append({
            "pdf": pdf_name,
            "page": found_pg,
            "course_code": c,
            "extracted_topics": " | ".join(tops),
            "human_ok": ""
        })

    pd.DataFrame(check_rows).to_csv(project_root / "DATA" / "review" / "extraction_check.csv", index=False)
    pd.DataFrame(targeted_rows).to_csv(project_root / "DATA" / "review" / "extraction_targeted.csv", index=False)
    print("✅ Step 5: Regenerated extraction_check.csv and created extraction_targeted.csv with PNGs.")

if __name__ == "__main__":
    main()

