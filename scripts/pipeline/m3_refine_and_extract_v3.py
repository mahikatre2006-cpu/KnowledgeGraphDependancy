import sys, re, json, random
import pymupdf
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter

project_root = Path(r"c:\Users\Siddhesh\Documents\KnowledgeGraphDependancy")
sys.path.insert(0, str(project_root))

def is_non_ascii_math(s):
    if re.search(r'[^\x00-\x7F]', s):
        return True
    if "≥" in s or "≤" in s or "≠" in s or "≈" in s: return True
    if re.search(r'[A-Za-z]\s*[≥≤≠≈><]\s*\d', s): return True
    return False

def is_stoplist(s):
    stops = {'and', 'or', 'the', 'introduction', 'overview', 'etc', 'etc.', 'unit', 'module', 'a', 'an', 'to', 'of', 'in', 'for', 'with', 'from', 'by', 'on', 'at', 'as', 'but', 'nor', 'so', 'yet'}
    words = s.lower().split()
    if len(words) == 1 and words[0] in stops:
        return True
    return False

def clean_and_split_topics_v3(raw_text):
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    joined_lines = []
    
    for line in lines:
        is_bullet = re.match(r'^(\d+\.\d+|\d+\.|[ivxlcdm]+\.|[IVXLCDM]+\.|[a-zA-Z]\)|[\u2022\-\*\>])', line)
        if not joined_lines:
            joined_lines.append(line)
        else:
            prev_line = joined_lines[-1]
            if not is_bullet and not prev_line.endswith(('.', ';', ':')):
                joined_lines[-1] = prev_line + " " + line
            else:
                joined_lines.append(line)
                
    topics = []
    for line in joined_lines:
        if ':' in line:
            parts = line.split(':', 1)
            heading = parts[0].strip()
            items_str = parts[1].strip()
            if heading:
                topics.append(heading)
        else:
            items_str = line
            
        def split_items(s):
            res = []
            cur = []
            paren_level = 0
            for char in s:
                if char == '(': paren_level += 1
                elif char == ')': paren_level = max(0, paren_level - 1)
                
                if (char == ',' and paren_level == 0) or char == ';':
                    res.append("".join(cur).strip())
                    cur = []
                else:
                    cur.append(char)
            if cur:
                res.append("".join(cur).strip())
            return res
            
        for item in split_items(items_str):
            item = item.strip()
            # Note: keeping space \s+ requirement so it only splits inner bullets not accidental matches
            sub_items = re.split(r'\s+(?:\d+\.\d+|\d+\.|[ivxlcdm]+\.|[IVXLCDM]+\.|[a-zA-Z]\)|[\u2022\-\*\>])\s+', item)
            for sub in sub_items:
                if sub.strip():
                    topics.append(sub.strip())

    final_topics = []
    for t in topics:
        t = re.sub(r'^(\d+\.\d+|\d+\.|[ivxlcdm]+\.|[IVXLCDM]+\.|[a-zA-Z]\)|[\u2022\-\*\>])\s*', '', t, flags=re.I)
        t = t.rstrip('.,;:- ')
        t = t.strip()
        
        if is_non_ascii_math(t): continue
        if len(t) < 2: continue
        if re.fullmatch(r'[\d\s\.\,\(\)\*\+\/\-]+', t): continue
        if is_stoplist(t): continue
            
        final_topics.append(t)
        
    return final_topics

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
                            topics = clean_and_split_topics_v3("\n".join(current_raw_text))
                            # Deduplicate case-insensitively while preserving order
                            seen = set()
                            dedup = []
                            for t in topics:
                                tl = t.lower()
                                if tl not in seen:
                                    seen.add(tl)
                                    dedup.append(t)
                            courses[current_code] = (current_code, current_name, dedup, current_raw_text)
                        
                        if current_code != code:
                            current_code = code
                            current_name = name_part
                            current_raw_text = []
                            continue
                            
            if current_code:
                if re.match(r'^(\d+\.\d+|[ivx]+\.)', line_str) or current_raw_text:
                    if "Text Books" in line_str or "References" in line_str or "Assessment" in line_str or "Term Work" in line_str:
                        topics = clean_and_split_topics_v3("\n".join(current_raw_text))
                        seen = set()
                        dedup = []
                        for t in topics:
                            tl = t.lower()
                            if tl not in seen:
                                seen.add(tl)
                                dedup.append(t)
                        courses[current_code] = (current_code, current_name, dedup, current_raw_text)
                        current_code = None
                        current_raw_text = []
                    elif line_str and not re.match(r'^\d+$', line_str):
                        current_raw_text.append(line_str)
                        
    if current_code and current_raw_text:
        topics = clean_and_split_topics_v3("\n".join(current_raw_text))
        seen = set()
        dedup = []
        for t in topics:
            tl = t.lower()
            if tl not in seen:
                seen.add(tl)
                dedup.append(t)
        courses[current_code] = (current_code, current_name, dedup, current_raw_text)
        
    return courses, expected_codes, doc

def main():
    print("=== Step 1: LOCATE IT file & Granularity ===")
    final_ds_path = project_root / "True_Cleaned_Dataset" / "final_training_dataset.csv"
    if final_ds_path.exists():
        print(f"Located IT file at: {final_ds_path}")
        df_final = pd.read_csv(final_ds_path)
        # Assuming source_syllabus has Information-Technology
        it_df = df_final[df_final['source_syllabus'].str.contains('Information-Technology', na=False, case=False)]
        
        it_topics_per_subject = []
        for course, group in it_df.groupby('Course_Code'):
            topics = set(group['concept_a']).union(set(group['concept_b']))
            it_topics_per_subject.append(len(topics))
        
        if it_topics_per_subject:
            it_min = np.min(it_topics_per_subject)
            it_median = np.median(it_topics_per_subject)
            it_max = np.max(it_topics_per_subject)
            print(f"IT Subjects Topics: min={it_min}, median={it_median}, max={it_max}")
        else:
            print("IT Subjects Topics: None found matching 'Information-Technology'.")
    else:
        print(f"IT file not found at {final_ds_path}")

    print("\n=== Step 2: New Topic Rule on COMPS ===")
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
        
        for code, (c, n, t, raw) in courses.items():
            match = re.search(r'\D(\d)\d{2,3}', code)
            true_sem = f"sem-{match.group(1)}" if match else sem_tag
            
            if code in registry:
                existing_sem = registry[code]['true_sem']
                existing_file = registry[code]['file']
                if sem_tag == true_sem and existing_sem != existing_file:
                    registry[code] = {'file': pdf_name, 'true_sem': true_sem, 'course': (c, n, t, raw)}
            else:
                registry[code] = {'file': pdf_name, 'true_sem': true_sem, 'course': (c, n, t, raw)}
                
    # Add CSDC7021 explicitly
    doc78 = docs["be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf"]
    for i, page in enumerate(doc78):
        if "CSDC7021" in page.get_text():
            text = page.get_text() + "\n" + (doc78[i+1].get_text() if i+1 < len(doc78) else "")
            lines = text.split('\n')
            in_syllabus = False
            raw_text = []
            for line in lines:
                if re.match(r'^(\d+\.\d+|[ivx]+\.)', line.strip()):
                    in_syllabus = True
                if in_syllabus:
                    if "Text Books" in line or "References" in line or "Assessment" in line:
                        break
                    raw_text.append(line.strip())
            if raw_text:
                topics = clean_and_split_topics_v3("\n".join(raw_text))
                seen = set()
                dedup = []
                for topic in topics:
                    tl = topic.lower()
                    if tl not in seen:
                        seen.add(tl)
                        dedup.append(topic)
                registry["CSDC7021"] = {'file': "be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf", 
                                    'true_sem': 'sem-7', 'course': ("CSDC7021", "CSDC7021", dedup, raw_text)}
            break

    comps_counts = [len(v['course'][2]) for k, v in registry.items() if not re.match(r'^(CSL|CSP|CSM|ILO)', k)]
    comps_min = np.min(comps_counts)
    comps_median = np.median(comps_counts)
    comps_max = np.max(comps_counts)
    print(f"COMPS Topics per Subject: min={comps_min}, median={comps_median}, max={comps_max}")

    print("\n=== Step 3: REAL EXAMPLES ===")
    random.seed(42)
    # Grab 10 random blocks from COMPS
    all_blocks_comps = []
    for code, v in registry.items():
        if not re.match(r'^(CSL|CSP|CSM|ILO)', code):
            all_blocks_comps.append((code, v['course'][3], v['course'][2]))
            
    samples_comps = random.sample(all_blocks_comps, min(10, len(all_blocks_comps)))
    for code, raw, topics in samples_comps:
        # Just grab the first chunk to print (approx 4-6 lines)
        sample_raw = "\n".join(raw[:6])
        print(f"\n[{code}] Raw (first 6 lines):\n{sample_raw}")
        print(f"-> Extracted Topics (first 10):\n{topics[:10]}")
        
    print("\nIT Examples (using same rule):")
    it_pdf_path = project_root / "DATA" / "raw" / "2019-scheme" / "Information-Technology" / "sem-3-IT.pdf"
    if it_pdf_path.exists():
        courses_it, _, _ = extract_from_pdf(it_pdf_path, skip_labs=True)
        it_blocks = list(courses_it.items())
        samples_it = random.sample(it_blocks, min(3, len(it_blocks)))
        for code, (c, n, t, raw) in samples_it:
            sample_raw = "\n".join(raw[:6])
            print(f"\n[{code}] Raw (first 6 lines):\n{sample_raw}")
            print(f"-> Extracted Topics (first 10):\n{t[:10]}")
    else:
        print("IT pdf sem-3-IT.pdf not found.")

    print("\n=== Step 4: BLANK PAGES ===")
    blank_targets = [
        ("be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf", 1),
        ("be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf", 8),
        ("be_computer-engineering_third-year-te-semester-6-rev-2019-c-scheme.pdf", 34),
        ("be_computer-engineering_third-year-te-semester-6-rev-2019-c-scheme.pdf", 27)
    ]
    blank_misssed_count = 0
    blank_no_content_count = 0
    for pdf, page_num in blank_targets:
        doc = docs.get(pdf)
        if doc and page_num < len(doc):
            page_text = doc[page_num].get_text()
            lines = page_text.splitlines()[:25]
            
            # Classification
            if "DETAILED SYLLABUS" in page_text or re.search(r'\d+\.\d+', page_text):
                # looks like syllabus content
                classification = "MISSED"
                blank_misssed_count += 1
            else:
                classification = "NO_SYLLABUS_CONTENT"
                blank_no_content_count += 1
                
            print(f"\nPage: {pdf} - {page_num} -> {classification}")
            for l in lines: print(f" | {l.strip()}")
            

    print("\n=== Step 5: TOP SHORT TOPICS ===")
    all_topics = []
    for code, v in registry.items():
        if not re.match(r'^(CSL|CSP|CSM|ILO)', code):
            all_topics.extend(v['course'][2])
            
    short_topics = [t for t in all_topics if len(t) < 8]
    counter = Counter(short_topics)
    print("30 most frequent short topics (< 8 chars):")
    for t, c in counter.most_common(30):
        print(f"  - '{t}' ({c} times)")


    print("\n=== Step 6: REGENERATE CSVs ===")
    out_dir = project_root / "DATA" / "review" / "extraction_pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    check_rows = []
    targeted_rows = []
    
    random.seed(42)
    for pdf_name in [p[1] for p in pdfs]:
        doc = docs[pdf_name]
        valid_pages = []
        for i in range(len(doc)):
            text = doc[i].get_text("text").strip()
            if len(text) > 50:
                # ONLY pages containing syllabus content
                if "DETAILED SYLLABUS" in text or "Course Contents" in text or re.search(r'\d+\.\d+', text):
                    valid_pages.append(i)
                    
        sample_pages = random.sample(valid_pages, min(3, len(valid_pages)))
        
        pdf_courses = [v['course'] for v in registry.values() if v['file'] == pdf_name]
        
        for pg_num in sample_pages:
            page = doc[pg_num]
            pix = page.get_pixmap(dpi=150)
            pix.save(str(out_dir / f"{pdf_name}_page_{pg_num}.png"))
            
            text = page.get_text("text").replace('\n', ' ')
            found_topics = []
            for c, n, tops, raw in pdf_courses:
                for t in tops:
                    if t[:20] in text:
                        found_topics.append(t)
            check_rows.append({
                "pdf": pdf_name,
                "page": pg_num,
                "extracted_topics": " | ".join(found_topics),
                "human_ok": ""
            })

    # Targeted: subjects whose topic count changed by >25% vs last run
    # (Since I don't have the last run counts in memory, I'll compare against IT median of 17 (or 69 vs 30).
    # Wait, the user said: "changed by more than 25% versus the last run".
    # I can just load mu_comp_eng_new_pairs.csv to count how many topics they had in the last run!
    pairs_csv_path = project_root / "DATA" / "candidates" / "mu_comp_eng_new_pairs.csv"
    if pairs_csv_path.exists():
        df_old_pairs = pd.read_csv(pairs_csv_path)
        old_counts = {}
        for c, g in df_old_pairs.groupby('Course_Code'):
            old_counts[c] = len(set(g['concept_a']).union(set(g['concept_b'])))
            
        for c, n, tops, raw in [v['course'] for v in registry.values() if not re.match(r'^(CSL|CSP|CSM|ILO)', v['course'][0])]:
            old_c = old_counts.get(c, 0)
            new_c = len(tops)
            if old_c > 0:
                change = abs(new_c - old_c) / old_c
                if change > 0.25:
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
    
    if not targeted_rows:
        print("Targeted rows is empty. No subject changed by >25%.")
    else:
        pd.DataFrame(targeted_rows).to_csv(project_root / "DATA" / "review" / "extraction_targeted.csv", index=False)
        print(f"Created extraction_targeted.csv with {len(targeted_rows)} subjects.")

    pd.DataFrame(check_rows).to_csv(project_root / "DATA" / "review" / "extraction_check.csv", index=False)
    
    print("\n=== STOP & NUMBERS ===")
    print(f"IT Granularity (min/median/max): {it_min}/{it_median}/{it_max}")
    print(f"COMPS Granularity (min/median/max): {comps_min}/{comps_median}/{comps_max}")
    print(f"Blank pages: {blank_misssed_count} missed, {blank_no_content_count} no syllabus content.")
    
if __name__ == "__main__":
    main()

