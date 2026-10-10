import sys, re, json, random
import pymupdf
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter

project_root = Path(r"c:\Users\Siddhesh\Documents\KnowledgeGraphDependancy")
sys.path.insert(0, str(project_root))

from scripts.pipeline.audit_dataset import check_person_name

def is_non_ascii_math(s):
    if re.search(r'[^\x00-\x7F]', s): return True
    if "≥" in s or "≤" in s or "≠" in s or "≈" in s: return True
    if re.search(r'[A-Za-z]\s*[≥≤≠≈><]\s*\d', s): return True
    return False

def is_stoplist(s):
    stops = {'and', 'or', 'the', 'introduction', 'overview', 'etc', 'etc.', 'unit', 'module', 'a', 'an', 'to', 'of', 'in', 'for', 'with', 'from', 'by', 'on', 'at', 'as', 'but', 'nor', 'so', 'yet'}
    words = s.lower().split()
    if len(words) == 1 and words[0] in stops:
        return True
    return False

PUBLISHERS = [
    'Wiley', 'PHI', 'TMH', 'Pearson', 'McGraw Hill', 'McGraw-Hill', 'Tata McGraw', 'Cengage',
    'Oxford', 'Khanna', 'Springer', 'Elsevier', 'Prentice Hall', 'Addison', 'Wesley', 'Narosa',
    'Technical Publications', 'Techmax', 'Vikas', 'S Chand', 'Nirali', 'ISBN', 'Edition',
    'Publication', 'Publishers', 'Press'
]

def check_publisher(s):
    sl = s.lower().strip()
    for pub in PUBLISHERS:
        publ = pub.lower()
        if sl == publ or sl.startswith(publ + ' ') or sl.startswith(publ + ',') or sl.startswith(publ + '.'):
            return True
    return False

def clean_and_split_topics_v4(raw_text):
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
            sub_items = re.split(r'\s+(?:\d+\.\d+|\d+\.|[ivxlcdm]+\.|[IVXLCDM]+\.|[a-zA-Z]\)|[\u2022\-\*\>])\s+', item)
            for sub in sub_items:
                if sub.strip():
                    topics.append(sub.strip())

    final_topics = []
    dropped_info = []
    for t in topics:
        t = re.sub(r'^(\d+\.\d+|\d+\.|[ivxlcdm]+\.|[IVXLCDM]+\.|[a-zA-Z]\)|[\u2022\-\*\>])\s*', '', t, flags=re.I)
        t = t.rstrip('.,;:- ')
        t = t.strip()
        
        if is_non_ascii_math(t): continue
        if len(t) < 2: continue
        if re.fullmatch(r'[\d\s\.\,\(\)\*\+\/\-]+', t): continue
        if is_stoplist(t): continue
            
        if check_publisher(t):
            dropped_info.append(('Publisher', t))
            continue
        
        if check_person_name(t):
            dropped_info.append(('Author Name', t))
            continue
            
        final_topics.append(t)
        
    return final_topics, dropped_info

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
                            topics, drops = clean_and_split_topics_v4("\n".join(current_raw_text))
                            seen = set()
                            dedup = []
                            for t in topics:
                                tl = t.lower()
                                if tl not in seen:
                                    seen.add(tl)
                                    dedup.append(t)
                            courses[current_code] = (current_code, current_name, dedup, current_raw_text, drops)
                        
                        if current_code != code:
                            current_code = code
                            current_name = name_part
                            current_raw_text = []
                            continue
                            
            if current_code:
                if re.match(r'^(\d+\.\d+|[ivx]+\.)', line_str) or current_raw_text:
                    if re.match(r'^(Text Books?|Reference Books?|References|Assessment|Term Work)', line_str, re.I):
                        topics, drops = clean_and_split_topics_v4("\n".join(current_raw_text))
                        seen = set()
                        dedup = []
                        for t in topics:
                            tl = t.lower()
                            if tl not in seen:
                                seen.add(tl)
                                dedup.append(t)
                        courses[current_code] = (current_code, current_name, dedup, current_raw_text, drops)
                        current_code = None
                        current_raw_text = []
                    elif line_str and not re.match(r'^\d+$', line_str):
                        current_raw_text.append(line_str)
                        
    if current_code and current_raw_text:
        topics, drops = clean_and_split_topics_v4("\n".join(current_raw_text))
        seen = set()
        dedup = []
        for t in topics:
            tl = t.lower()
            if tl not in seen:
                seen.add(tl)
                dedup.append(t)
        courses[current_code] = (current_code, current_name, dedup, current_raw_text, drops)
        
    return courses, expected_codes, doc

def main():
    print("=== Step 1: PUBLISHER/AUTHOR CONTAMINATION ===")
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
    
    all_dropped = []
    
    for sem_tag, pdf_name in pdfs:
        pdf_path = pdf_dir / pdf_name
        courses, expected_codes, doc = extract_from_pdf(pdf_path, skip_labs=False)
        docs[pdf_name] = doc
        
        for code, (c, n, t, raw, drops) in courses.items():
            match = re.search(r'\D(\d)\d{2,3}', code)
            true_sem = f"sem-{match.group(1)}" if match else sem_tag
            
            if code in registry:
                existing_sem = registry[code]['true_sem']
                existing_file = registry[code]['file']
                if sem_tag == true_sem and existing_sem != existing_file:
                    registry[code] = {'file': pdf_name, 'true_sem': true_sem, 'course': (c, n, t, raw)}
                    all_dropped.extend(drops)
            else:
                registry[code] = {'file': pdf_name, 'true_sem': true_sem, 'course': (c, n, t, raw)}
                all_dropped.extend(drops)
                
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
                    if re.match(r'^(Text Books?|Reference Books?|References|Assessment|Term Work)', line.strip(), re.I):
                        break
                    raw_text.append(line.strip())
            if raw_text:
                topics, drops = clean_and_split_topics_v4("\n".join(raw_text))
                all_dropped.extend(drops)
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

    drop_counts = Counter([typ for typ, val in all_dropped])
    for typ, count in drop_counts.items():
        print(f"\nDropped via {typ} filter: {count}")
        items = list(set([val for t, val in all_dropped if t == typ]))[:15]
        for it in items: print(f"  - {it}")
        
    print("\nReference text feed check: Explicit block termination on 'Text Books', 'References', 'Reference Books' ensures no reference sections are captured as topics.")
    
    # Check surviving topics
    surviving_suspects = []
    for code, v in registry.items():
        if not re.match(r'^(CSL|CSP|CSM|ILO)', code):
            for t in v['course'][2]:
                if any(pub.lower() in t.lower() for pub in PUBLISHERS):
                    surviving_suspects.append(t)
    print(f"\nSurviving topics matching publisher keywords (substring matches kept intentionally e.g. 'Compression Edition'): {len(surviving_suspects)}")
    for t in set(surviving_suspects[:5]):
        print(f"  - {t}")


    print("\n=== Step 2: SAMPLER BIAS ===")
    
    # Pre-calculate content pages
    pdf_content_pages = {p: set() for _, p in pdfs}
    
    # Cache page texts
    page_texts = {}
    for sem_tag, pdf_name in pdfs:
        doc = docs[pdf_name]
        page_texts[pdf_name] = [page.get_text("text").replace('\n', ' ') for page in doc]

    for code, v in registry.items():
        pdf_name = v['file']
        cached_texts = page_texts[pdf_name]
        for t in v['course'][2]:
            t_sub = t[:20]
            for i, text in enumerate(cached_texts):
                if t_sub in text:
                    pdf_content_pages[pdf_name].add(i)

    for sem_tag, pdf_name in pdfs:
        doc = docs[pdf_name]
        total = len(doc)
        content_count = len(pdf_content_pages[pdf_name])
        
        # Old filter count
        old_filter = 0
        for i, page in enumerate(doc):
            text = page.get_text("text")
            if "DETAILED SYLLABUS" in text or "Course Contents" in text:
                old_filter += 1
                
        print(f"[{pdf_name}] Total Pages: {total}, CONTENT Pages (>=1 extracted topic): {content_count}, Old Filter Pages: {old_filter}")


    print("\n=== Step 4: IT vs COMPS GRANULARITY (CORRECTLY) ===")
    final_ds_path = project_root / "True_Cleaned_Dataset" / "final_training_dataset.csv"
    if final_ds_path.exists():
        df_final = pd.read_csv(final_ds_path)
        # Using the whole final_training_dataset.csv since we verified it holds 1171 rows and is the IT dataset output
        it_topics_per_subject = []
        for course, group in df_final.groupby('Course_Code'):
            topics = set(group['concept_a']).union(set(group['concept_b']))
            it_topics_per_subject.append(len(topics))
            
        it_min = np.min(it_topics_per_subject)
        it_median = np.median(it_topics_per_subject)
        it_max = np.max(it_topics_per_subject)
        print(f"IT Granularity (from True_Cleaned_Dataset/final_training_dataset.csv): min={it_min}, median={it_median}, max={it_max}")
    else:
        print("IT Granularity: final_training_dataset.csv not found.")
        it_min = it_median = it_max = 0

    comps_counts = [len(v['course'][2]) for k, v in registry.items() if not re.match(r'^(CSL|CSP|CSM|ILO)', k)]
    comps_min = np.min(comps_counts)
    comps_median = np.median(comps_counts)
    comps_max = np.max(comps_counts)
    print(f"COMPS Granularity: min={comps_min}, median={comps_median}, max={comps_max}")
    
    print("\nPair Generation Methods:")
    print("IT: Generated using a sliding window across syllabus order (e.g., pairs formed within a max positional gap of 15).")
    print("COMPS: Proposed using Top-8-similar embeddings plus adjacent pairs.")
    print("\nDependent Features:")
    print(" - 'order_delta': Distance in syllabus position between concept A and B.")
    
    if final_ds_path.exists():
        it_order_delta = df_final['order_delta'].dropna()
        print(f"IT 'order_delta' Mean: {it_order_delta.mean():.2f}, Std Dev: {it_order_delta.std():.2f}")
    
    print("PLAN: After COMPS candidates are generated, we will compute 'order_delta' for them and compare against the IT mean and spread to ensure candidate generation isn't injecting systemic bias.")


    print("\n=== Step 3 & 6: REGENERATE CSVs ===")
    out_dir = project_root / "DATA" / "review" / "extraction_pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    check_rows = []
    targeted_rows = []
    
    random.seed(42)
    for pdf_name in [p[1] for p in pdfs]:
        doc = docs[pdf_name]
        valid_pages = sorted(list(pdf_content_pages[pdf_name]))
        
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

    # Targeted
    pairs_csv_path = project_root / "DATA" / "candidates" / "mu_comp_eng_new_pairs.csv"
    old_counts = {}
    if pairs_csv_path.exists():
        df_old_pairs = pd.read_csv(pairs_csv_path)
        for c, g in df_old_pairs.groupby('Course_Code'):
            old_counts[c] = len(set(g['concept_a']).union(set(g['concept_b'])))
            
    for c, n, tops, raw in [v['course'] for v in registry.values() if not re.match(r'^(CSL|CSP|CSM|ILO)', v['course'][0])]:
        old_c = old_counts.get(c, 0)
        new_c = len(tops)
        changed = False
        if old_c > 0:
            change = abs(new_c - old_c) / old_c
            if change > 0.25:
                changed = True
                
        if changed or new_c < 15 or new_c > 90:
            pdf_name = registry[c]['file']
            doc = docs[pdf_name]
            # Find a page containing this subject
            found_pg = 0
            for pg in sorted(list(pdf_content_pages[pdf_name])):
                if any(t[:20] in doc[pg].get_text("text").replace('\n', ' ') for t in tops):
                    found_pg = pg
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
    print(f"Created extraction_targeted.csv with {len(targeted_rows)} subjects.")
    
if __name__ == "__main__":
    main()

