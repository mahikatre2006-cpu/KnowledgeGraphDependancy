import sys
import re
import json
import pymupdf
import numpy as np
import pandas as pd
from pathlib import Path

project_root = Path(r"c:\Users\Siddhesh\Documents\KnowledgeGraphDependancy")
sys.path.insert(0, str(project_root))

from scripts.pipeline.full_pipeline import build_candidate_pairs
from scripts.pipeline.audit_dataset import (
    check_person_name, check_publisher_citation, check_admin_rubric, 
    check_tool_fragment, check_length_bound, check_truncated_fragment
)

def custom_comps_extractor(pdf_path: Path):
    """
    Custom extractor for the 2019 COMPS scheme layout.
    Avoids touching full_pipeline.py regexes.
    Matches Course Codes like CSC301, CSL301.
    Matches topics using 'd.d' decimal numbering (e.g. '1.1 Topic text').
    """
    doc = pymupdf.open(str(pdf_path))
    courses = []
    
    current_code = None
    current_name = None
    current_topics = []
    
    for i, page in enumerate(doc):
        text = page.get_text("text")
        
        # Look for course headers (CSC301, CSL301, CSD301, CSP301, CBL301)
        # Usually they appear at the top of the course tables
        # Also include TE and BE codes if they follow similar patterns
        code_matches = re.finditer(r'(CS[A-Z]\d{3}|CB[A-Z]\d{3})\s*\n\s*(.+)', text)
        for match in code_matches:
            code = match.group(1).strip()
            name = match.group(2).strip()
            if len(name) > 3 and "Credits" not in name and "Course Name" not in name:
                if current_code and current_code != code and current_topics:
                    courses.append((current_code, current_name, current_topics))
                    current_topics = []
                if not current_code or current_code != code:
                    current_code = code
                    current_name = name
                    current_topics = []
                    
        # Extract topics
        if current_code:
            lines = text.split('\n')
            curr_topic_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Match "1.1 Topic text"
                if re.match(r'^\d+\.\d+', line):
                    if curr_topic_lines:
                        current_topics.append(" ".join(curr_topic_lines))
                    curr_topic_lines = [line]
                elif curr_topic_lines:
                    # Stop accumulating if we hit a single digit (module number),
                    # "Self-learning", or a capitalized word indicating a new section
                    if (len(line) < 3 or re.match(r'^\d+$', line) or 
                        'Self-learning' in line or 
                        'Self Learning' in line or 
                        re.match(r'^Text\s*Books', line, re.I) or
                        re.match(r'^References', line, re.I) or
                        re.match(r'^Assessment', line, re.I) or
                        re.match(r'^\*{2,}', line)):
                        current_topics.append(" ".join(curr_topic_lines))
                        curr_topic_lines = []
                    else:
                        curr_topic_lines.append(line)
            if curr_topic_lines:
                current_topics.append(" ".join(curr_topic_lines))
                
    if current_code and current_topics:
        courses.append((current_code, current_name, current_topics))
        
    # Deduplicate courses by code (keep the one with most topics)
    unique_courses = {}
    for c, n, t in courses:
        if c not in unique_courses or len(t) > len(unique_courses[c][2]):
            unique_courses[c] = (c, n, t)
            
    return list(unique_courses.values())


def main():
    pdf_dir = project_root / "DATA" / "raw" / "2019-scheme" / "Computer-Engineering"
    pdfs = [
        "be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf",
        "be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf",
        "be_computer-engineering_third-year-te-semester-5-rev-2019-c-scheme.pdf",
        "be_computer-engineering_third-year-te-semester-6-rev-2019-c-scheme.pdf",
        "be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf",
    ]

    print("=== Step A: Diagnosis ===")
    all_courses = []
    
    for pdf_name in pdfs:
        pdf_path = pdf_dir / pdf_name
        doc = pymupdf.open(str(pdf_path))
        
        char_counts = []
        img_counts = []
        page3_text = ""
        for i, page in enumerate(doc):
            text = page.get_text()
            char_counts.append(len(text))
            img_counts.append(len(page.get_images(full=True)))
            if i == 2:
                page3_text = text[:300].replace('\n', ' ')
                
        med_chars = np.median(char_counts)
        verdict = "TEXT_LAYER" if med_chars >= 200 else ("SCANNED" if med_chars < 50 else "MIXED")
        
        print(f"\n--- {pdf_name} ---")
        print(f"Pages: {len(doc)}")
        print(f"Chars/page: min={np.min(char_counts):.0f}, median={med_chars:.0f}, max={np.max(char_counts):.0f}")
        print(f"Images/page: median={np.median(img_counts):.0f}, max={np.max(img_counts):.0f}")
        print(f"Verdict: {verdict}")
        print(f"Page 3 preview: {page3_text.encode('utf-8', 'ignore').decode('utf-8')}")
        
        if verdict == "TEXT_LAYER":
            samples = []
            for page in doc:
                for line in page.get_text().split('\n'):
                    if 'Module' in line or 'CSC' in line or 'CSL' in line:
                        samples.append(line.strip())
                        if len(samples) == 3: break
                if len(samples) == 3: break
            print("Samples:")
            for s in samples:
                print(f"  - {s.encode('utf-8', 'ignore').decode('utf-8')}")
            
            print("Failure Reason: The existing extractor in full_pipeline.py relies on COURSE_CODE_RE (7-digit codes like 1234567) and DETAIL_HDR_RE ('Detailed Syllabus'). The COMPS 2019 scheme uses 'CSC301'/'CSL301' style codes and no 'Detailed Syllabus' header, causing 0 matches.")
            
        print("\nApplying custom COMPS extractor (fixing layout without touching existing regexes)...")
        courses = custom_comps_extractor(pdf_path)
        
        pdf_total_raw = sum(len(topics) for _, _, topics in courses)
        clean_courses = []
        pdf_clean_count = 0
        pdf_filtered = 0
        
        for code, name, topics in courses:
            clean_topics = []
            for t in topics:
                if (check_person_name(t) or check_publisher_citation(t) or 
                    check_admin_rubric(t) ):
                    pdf_filtered += 1
                else:
                    # Minor cleanup for numbering (remove the leading '1.1 ' for purity)
                    t_clean = re.sub(r'^\d+\.\d+\s*', '', t)
                    clean_topics.append(t_clean)
                    
            pdf_clean_count += len(clean_topics)
            if clean_topics:
                clean_courses.append((code, name, clean_topics))
                
        print(f"Extraction Results for {pdf_name}:")
        print(f"  Subjects: {len(clean_courses)} (raw: {len(courses)})")
        print(f"  Raw topics: {pdf_total_raw}")
        print(f"  Filtered out: {pdf_filtered} (author/publisher/exam/length)")
        print(f"  Clean topics: {pdf_clean_count}")
        
        # Save JSON
        out_json = project_root / "DATA" / "extracted" / f"{pdf_name}.json"
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump([{"course_code": c, "course_name": n, "topics": t} for c,n,t in clean_courses], f, indent=2)
            
        # Attach pdf_name for build_candidate_pairs
        tagged = [(pdf_name, code, name, t) for code, name, t in clean_courses]
        all_courses.extend(tagged)
        
    print("\n=== Generating Pairs ===")
    df_new = build_candidate_pairs(all_courses)
    out_csv = project_root / "DATA" / "candidates" / "mu_comp_eng_new_pairs.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_new.to_csv(out_csv, index=False)
    print(f"✅ Step A: Wrote {len(df_new)} candidate pairs for {len(all_courses)} subjects to {out_csv.name}")

if __name__ == "__main__":
    main()
