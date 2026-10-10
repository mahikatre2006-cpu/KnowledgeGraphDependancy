import sys, re, json, random
import pymupdf
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

project_root = Path(r"c:\Users\Siddhesh\Documents\KnowledgeGraphDependancy")
sys.path.insert(0, str(project_root))

from scripts.pipeline.audit_dataset import (
    check_person_name, check_publisher_citation, check_admin_rubric
)

def keep_short(token):
    if len(token) < 3: return False
    if len(token) > 5: return True
    if token.isupper(): return True
    # alphanumeric like 3NF/1NF
    has_digit = any(c.isdigit() for c in token)
    has_alpha = any(c.isalpha() for c in token)
    if has_digit and has_alpha: return True
    return False

def clean_and_split_topics(raw_text):
    raw_topics = []
    lines = raw_text.split('\n')
    for line in lines:
        if ':' in line:
            parts = line.split(':', 1)
            raw_topics.append(parts[0])
            for seg in parts[1].split(','):
                raw_topics.append(seg)
        else:
            for seg in line.split(','):
                raw_topics.append(seg)
                
    topics = []
    for seg in raw_topics:
        seg = seg.strip()
        seg = re.sub(r'^(\d+\.\d+|\d+\.|[ivx]+\.)\s*', '', seg, flags=re.I)
        seg = seg.strip()
        
        # Remove 1-2 generic word fragments if they are too short and not a special acronym
        words = seg.split()
        if len(words) <= 2 and len(seg) < 8:
            if not keep_short(seg):
                continue
        elif not keep_short(seg):
            continue
            
        if not (check_person_name(seg) or check_publisher_citation(seg) or 
                check_admin_rubric(seg) or re.match(r'^Text\s*Books', seg, re.I) or 
                re.match(r'^References', seg, re.I) or re.match(r'^Assessment', seg, re.I) or
                "Self-learning" in seg or "Self Learning" in seg):
            
            if not re.fullmatch(r'[\d\s\-\.\,\(\)\*\+\/]+', seg):
                topics.append(seg)
    return topics

def get_expected_codes(doc):
    codes = set()
    for i in range(min(15, len(doc))):
        text = doc[i].get_text()
        found = re.findall(r'\b(?:CS[A-Z]{0,2}|CB[A-Z]{0,2}|IL[A-Z]{0,2})\d{3,4}\b', text)
        codes.update(found)
    return codes

def extract_from_pdf(pdf_path, skip_labs=True):
    doc = pymupdf.open(str(pdf_path))
    expected_codes = get_expected_codes(doc)
    
    courses = {}
    current_code = None
    current_name = None
    current_raw_text = []
    
    for i, page in enumerate(doc):
        text = page.get_text("text")
        lines = text.split('\n')
        for j, line in enumerate(lines):
            line_str = line.strip()
            code_match = re.match(r'^((?:CS[A-Z]{0,2}|CB[A-Z]{0,2}|IL[A-Z]{0,2})\d{3,4})\b', line_str)
            if code_match:
                code = code_match.group(1)
                if code in expected_codes:
                    if skip_labs and re.match(r'^(CSL|CSP|CSM|ILO)', code):
                        continue
                        
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
                            
            if current_code:
                if re.match(r'^(\d+\.\d+|[ivx]+\.)', line_str) or current_raw_text:
                    if "Text Books" in line_str or "References" in line_str or "Assessment" in line_str or "Term Work" in line_str:
                        courses[current_code] = (current_code, current_name, clean_and_split_topics("\n".join(current_raw_text)))
                        current_code = None
                        current_raw_text = []
                    elif line_str and not re.match(r'^\d+$', line_str):
                        current_raw_text.append(line_str)
                        
    if current_code and current_raw_text:
        courses[current_code] = (current_code, current_name, clean_and_split_topics("\n".join(current_raw_text)))
        
    return courses, expected_codes, doc

def main():
    print("=== Step 1: IT vs COMPS Granularity ===")
    
    # 1. IT vs COMPS topic granularity
    final_ds_path = project_root / "DATA" / "processed" / "final_training_dataset.csv"
    if final_ds_path.exists():
        df_final = pd.read_csv(final_ds_path)
        # Filter for IT (either by source_syllabus containing Information-Technology, or just the main ones)
        it_df = df_final[df_final['source_syllabus'].str.contains('Information-Technology', na=False, case=False)]
        
        it_topics_per_subject = []
        for course, group in it_df.groupby('Course_Code'):
            topics = set(group['concept_a']).union(set(group['concept_b']))
            it_topics_per_subject.append(len(topics))
        
        if it_topics_per_subject:
            print(f"IT Subjects Topics: min={np.min(it_topics_per_subject)}, median={np.median(it_topics_per_subject)}, max={np.max(it_topics_per_subject)}")
        else:
            print("IT Subjects Topics: None found.")
            
    print("\nSplit Rule Examples:")
    # Provide 5 examples for IT vs COMPS based on split rules
    raw_comps = [
        "Hashing: hash functions, collision resolution",
        "1.1 Introduction to ER, EER, and OODBMS",
        "Normal forms: 1NF, 2NF, 3NF, BCNF",
        "Introduction to AI, AI problems, AI techniques",
        "Trees, Binary Trees, Binary Search Trees"
    ]
    print("COMPS (and aligned IT) splitting rule in action:")
    for raw in raw_comps:
        print(f"Raw: {raw}")
        print(f"-> Topics: {clean_and_split_topics(raw)}\n")

    print("\n=== Step 2 & 3: Short Topics & Comma Fragments ===")
    pdf_dir = project_root / "DATA" / "raw" / "2019-scheme" / "Computer-Engineering"
    pdfs = [
        ("sem-3", "be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf"),
        ("sem-4", "be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf"),
        ("sem-5", "be_computer-engineering_third-year-te-semester-5-rev-2019-c-scheme.pdf"),
        ("sem-6", "be_computer-engineering_third-year-te-semester-6-rev-2019-c-scheme.pdf"),
        ("sem-7-8", "be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf"),
    ]

    registry = {}
    docs = {}
    
    for sem_tag, pdf_name in pdfs:
        pdf_path = pdf_dir / pdf_name
        courses, expected_codes, doc = extract_from_pdf(pdf_path, skip_labs=False)
        docs[pdf_name] = doc
        
        for code, (c, n, t) in courses.items():
            match = re.search(r'\D(\d)\d{2,3}', code)
            true_sem = f"sem-{match.group(1)}" if match else sem_tag
            
            if code in registry:
                existing_sem = registry[code]['true_sem']
                existing_file = registry[code]['file']
                if sem_tag == true_sem and existing_sem != existing_file:
                    registry[code] = {'file': pdf_name, 'true_sem': true_sem, 'course': (c, n, t)}
            else:
                registry[code] = {'file': pdf_name, 'true_sem': true_sem, 'course': (c, n, t)}

    # Analyze short topics and fragments
    all_topics = []
    for code, v in registry.items():
        # filter out labs for the analysis of theory topics
        if not re.match(r'^(CSL|CSP|CSM|ILO)', code):
            all_topics.extend(v['course'][2])
            
    comps_counts = [len(v['course'][2]) for k, v in registry.items() if not re.match(r'^(CSL|CSP|CSM|ILO)', k)]
    print(f"\nNew COMPS Topics per Subject: min={np.min(comps_counts)}, median={np.median(comps_counts)}, max={np.max(comps_counts)}")

    short_topics = [t for t in all_topics if len(t) < 8]
    print(f"\nRecovered topics shorter than 8 chars: {len(short_topics)}")
    
    counter = Counter(short_topics)
    print("30 most frequent short topics:")
    for t, c in counter.most_common(30):
        print(f"  - '{t}' ({c} times)")

    print("\n=== Step 4: Sem 7-8 Missing Codes ===")
    doc78 = docs["be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf"]
    expected78 = get_expected_codes(doc78)
    
    extracted78 = set(c for c, v in registry.items() if v['file'] == "be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf")
    missing = list(expected78 - extracted78)
    
    csdc = sorted([c for c in missing if c.startswith('CSDC')])
    ilo = sorted([c for c in missing if c.startswith('ILO')])
    labs = sorted([c for c in missing if re.match(r'^(CSL|CSP|CSM)', c)])
    
    print(f"\nMissing Theory Electives (CSDC): {csdc}")
    print(f"Missing Institute Electives (ILO): {ilo}")
    print(f"Missing Labs/Projects (CSDL/CSL/CSP): {labs}")
    
    for m_code in csdc:
        print(f"\nCode: {m_code}")
        for i, page in enumerate(doc78):
            if m_code in page.get_text():
                print(f"Found on page {i}")
                lines = page.get_text().splitlines()[:10]
                for l in lines: print(f" | {l.strip()}")
                break

    # Re-extract CSDC7021 if it has module structure
    for m_code in csdc:
        for i, page in enumerate(doc78):
            if m_code in page.get_text():
                # Extract logic for it
                print(f"\nExtracting {m_code} since it has a module structure (added to registry)")
                
                # Manual extraction snippet for CSDC codes
                name_match = re.search(f"{m_code}\s*(.*)", page.get_text())
                c_name = name_match.group(1).strip() if name_match else "Elective"
                
                raw_text = []
                # grab text from page i and i+1
                text = page.get_text() + "\n" + (doc78[i+1].get_text() if i+1 < len(doc78) else "")
                lines = text.split('\n')
                in_syllabus = False
                for line in lines:
                    if re.match(r'^(\d+\.\d+|[ivx]+\.)', line.strip()):
                        in_syllabus = True
                    if in_syllabus:
                        if "Text Books" in line or "References" in line or "Assessment" in line:
                            break
                        raw_text.append(line.strip())
                
                if raw_text:
                    topics = clean_and_split_topics("\n".join(raw_text))
                    registry[m_code] = {'file': "be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf", 
                                        'true_sem': 'sem-7', 'course': (m_code, c_name, topics)}
                    print(f"Extracted {len(topics)} topics for {m_code}")
                break


    print("\n=== Step 5: Pair Generation Cap ===")
    # Pair generation with Top 8 + adjacent
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    all_pairs = []
    pairs_per_subj = {}
    
    for code, v in registry.items():
        if re.match(r'^(CSL|CSP|CSM|ILO)', code): continue # skip labs and institute electives
        
        pdf_name = v['file']
        c, n, topics = v['course']
        
        if len(topics) < 2: continue
        
        # Embed all topics for this subject
        embeddings = model.encode(topics)
        sim_matrix = cosine_similarity(embeddings)
        
        subj_pairs = set()
        
        for i in range(len(topics)):
            # Top 8 by similarity
            # Exclude self
            sims = sim_matrix[i].copy()
            sims[i] = -1
            
            top_8_idx = sims.argsort()[-8:][::-1]
            for j in top_8_idx:
                pair = tuple(sorted([i, j]))
                subj_pairs.add(pair)
            
            # Adjacent pairs
            if i > 0:
                subj_pairs.add(tuple(sorted([i-1, i])))
            if i < len(topics) - 1:
                subj_pairs.add(tuple(sorted([i, i+1])))
                
        # Generate rows
        for i, j in subj_pairs:
            all_pairs.append({
                "concept_a": topics[i],
                "concept_b": topics[j],
                "source_syllabus": pdf_name,
                "Course_Code": code,
                "course_name": n,
                "order_delta": abs(j - i),
                "domain_match": 1,
                "label": ""
            })
        
        pairs_per_subj[code] = len(subj_pairs)
        print(f"  {code}: {len(subj_pairs)} pairs")
        
    df_pairs = pd.DataFrame(all_pairs)
    total_pairs = len(df_pairs)
    
    if total_pairs > 4000:
        print(f"\nTotal pairs ({total_pairs}) exceeds cap of 4000. Downsampling...")
        df_pairs = df_pairs.sample(n=4000, random_state=42).reset_index(drop=True)
    
    print(f"\nFinal Candidates Count: {len(df_pairs)}")
    calls_needed = len(df_pairs) / 50.0
    print(f"Estimated Gemini Calls (50 per batch): {calls_needed:.1f}")
    
    df_pairs.to_csv(project_root / "DATA" / "candidates" / "mu_comp_eng_new_pairs.csv", index=False)
    
    print("\n=== Step 6: Regenerate Review Files ===")
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

    final_courses = [v['course'] for v in registry.values() if not re.match(r'^(CSL|CSP|CSM|ILO)', v['course'][0])]
    targeted_subjects = [c for c in final_courses if len(c[2]) < 8]
    for c, n, tops in targeted_subjects:
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
    print("Regenerated extraction_check.csv and extraction_targeted.csv with PNGs.")
    
    print("\n=== SUMMARY AND STOP ===")
    print(f"Topics per subject: min={np.min(comps_counts)}, median={np.median(comps_counts)}, max={np.max(comps_counts)}")
    print(f"Recovered short topics: {len(short_topics)}")
    print(f"Candidate pair count: {len(df_pairs)}")
    print(f"Gemini call estimate: {calls_needed:.1f}")

if __name__ == "__main__":
    main()

