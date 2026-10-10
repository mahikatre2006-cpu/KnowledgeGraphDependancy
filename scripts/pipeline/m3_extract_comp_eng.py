import sys
from pathlib import Path
import pandas as pd
import re

project_root = Path(r"c:\Users\Siddhesh\Documents\KnowledgeGraphDependancy")
sys.path.insert(0, str(project_root))

from scripts.pipeline.full_pipeline import extract_course_blocks_from_pdf, build_candidate_pairs
from scripts.pipeline.audit_dataset import check_person_name, check_publisher_citation, check_admin_rubric, check_tool_fragment, check_length_bound, check_truncated_fragment

pdf_dir = project_root / "DATA" / "raw" / "2019-scheme" / "Computer-Engineering"
pdfs = [
    "be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf",
    "be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf",
    "be_computer-engineering_third-year-te-semester-5-rev-2019-c-scheme.pdf",
    "be_computer-engineering_third-year-te-semester-6-rev-2019-c-scheme.pdf",
    "be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf",
]

all_courses = []
zero_topics_found = False

for pdf_name in pdfs:
    pdf_path = pdf_dir / pdf_name
    
    # Fallback pattern for COMPS code matching if header parsing fails
    # Standard format often starts with CSC, CSL, etc.
    # extract_course_blocks_from_pdf handles general extraction, let's see what it returns
    courses = extract_course_blocks_from_pdf(pdf_path)
    
    pdf_total_raw = sum(len(topics) for _, _, topics in courses)
    
    clean_courses = []
    pdf_clean_count = 0
    pdf_filtered = 0
    
    for code, name, topics in courses:
        # Extra fallback: if code is unknown, assign a placeholder based on name to keep topics together
        if code == "UNKNOWN" and name != "UNKNOWN":
            code = "COMP_" + "".join(w[0] for w in str(name).split() if w.isalnum()).upper()
        
        clean_topics = []
        for t in topics:
            t_str = str(t)
            if (check_person_name(t_str) or 
                check_publisher_citation(t_str) or 
                check_admin_rubric(t_str) or
                check_length_bound(t_str)):
                pdf_filtered += 1
            else:
                clean_topics.append(t_str)
                
        pdf_clean_count += len(clean_topics)
        if clean_topics:
            clean_courses.append((code, name, clean_topics))
        
    print(f"PDF: {pdf_name}")
    print(f"  Subjects: {len(clean_courses)} (raw: {len(courses)})")
    print(f"  Raw topics: {pdf_total_raw}")
    print(f"  Filtered out: {pdf_filtered} (author/publisher/exam/length)")
    print(f"  Clean topics: {pdf_clean_count}")
    
    if pdf_clean_count == 0:
        print(f"  CRITICAL: 0 topics found in {pdf_name}. Halting to investigate OCR or extraction failure.")
        zero_topics_found = True
    
    # Attach pdf_name for build_candidate_pairs which expects (pdf_name, code, name, topics)
    tagged = [(pdf_name, code, name, t) for code, name, t in clean_courses]
    all_courses.extend(tagged)

if zero_topics_found:
    print("\nExtraction halted due to 0 clean topics in one or more PDFs.")
    sys.exit(1)

# Generate pairs
df_new = build_candidate_pairs(all_courses)

# Ensure columns
out_csv = project_root / "DATA" / "candidates" / "mu_comp_eng_new_pairs.csv"
out_csv.parent.mkdir(parents=True, exist_ok=True)
df_new.to_csv(out_csv, index=False)
print(f"\n✅ Step 0.5: Wrote {len(df_new)} candidate pairs for {len(all_courses)} subjects to {out_csv.name}")
