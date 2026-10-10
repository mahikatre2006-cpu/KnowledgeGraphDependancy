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

GENERIC_STANDALONE = {
    'basic concepts', 'types', 'definition', 'applications', 'overview', 'theory', 'relations', 'introduction'
}

def clean_and_split_topics_v5(raw_text, author_blocklist, report_dict):
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
    for t in topics:
        t = re.sub(r'^(\d+\.\d+|\d+\.|[ivxlcdm]+\.|[IVXLCDM]+\.|[a-zA-Z]\)|[\u2022\-\*\>])\s*', '', t, flags=re.I)
        t = t.rstrip('.,;:- ')
        t = t.strip()
        
        if is_non_ascii_math(t): continue
        if len(t) < 2: continue
        if re.fullmatch(r'[\d\s\.\,\(\)\*\+\/\-]+', t): continue
        if is_stoplist(t): continue
        
        # New Rule d:
        if t.lower() in GENERIC_STANDALONE:
            report_dict['dropped_generic'].append(t)
            continue
            
        # New Rule b:
        drop_reason = None
        
        # (i) contains blocklisted name
        for pat, name in author_blocklist:
            if pat.search(t):
                drop_reason = f"blocklisted_name ({name})"
                break
                
        # (ii) matches initials-and-surname
        if not drop_reason and re.search(r'\b[A-Z][a-z]*\s+[A-Z]\.\s+[A-Z][a-z]+', t):
            drop_reason = "initials_surname"
        elif not drop_reason and re.search(r'\b[A-Z]\.\s*[A-Z]\.\s+[A-Z][a-z]+', t):
            drop_reason = "initials_surname"
        
        # (iii) contains ISBN, edition, etc.
        if not drop_reason:
            t_lower = t.lower()
            if 'isbn' in t_lower or 'edition' in t_lower or 'publication' in t_lower or 'publishers' in t_lower or 'press' in t_lower:
                drop_reason = "isbn_edition_pub"
            elif re.search(r'\b(?:19|20)\d{2}\b', t):
                drop_reason = "year_19xx_20xx"
            else:
                for pub in PUBLISHERS:
                    if pub.lower() in t_lower:
                        drop_reason = "publisher_stoplist"
                        break
                        
        if drop_reason:
            if drop_reason not in report_dict:
                report_dict[drop_reason] = []
            report_dict[drop_reason].append(t)
            continue
            
        final_topics.append(t)
        
    return final_topics


def extract_authors(text):
    authors = []
    # 1. Initials format: A. B. Smith or A. Smith
    authors.extend(re.findall(r'\b(?:[A-Z]\.\s*){1,2}[A-Z][a-z]+\b', text))
    # 2. Smith, A. B.
    authors.extend(re.findall(r'\b[A-Z][a-z]+,\s*(?:[A-Z]\.\s*){1,2}\b', text))
    
    # 3. Names before the first comma or quote (typical reference start)
    m = re.match(r'^(?:\d+\.\s*)?([^,\'\"\(\:]+)', text)
    if m:
        chunk = m.group(1).strip()
        parts = re.split(r'\s+(?:and|&)\s+', chunk)
        for part in parts:
            words = part.strip().split()
            if 2 <= len(words) <= 3 and all(w and w[0].isupper() for w in words):
                if not any(w.lower() in {'learning', 'system', 'introduction', 'data', 'computer', 'engineering', 'programming', 'software', 'network', 'operating', 'machine', 'design', 'artificial', 'intelligence'} for w in words):
                    authors.append(" ".join(words))
    return set(authors)


def get_expected_codes(doc):
    codes = set()
    for i in range(min(15, len(doc))):
        text = doc[i].get_text()
        found = re.findall(r'\b(?:CS[A-Z]{0,2}|CB[A-Z]{0,2}|IL[A-Z]{0,2})\d{3,4}\b', text)
        codes.update(found)
    return codes


def extract_from_pdf_v5(pdf_path, skip_labs=True):
    doc = pymupdf.open(str(pdf_path))
    expected_codes = get_expected_codes(doc)
    
    courses = {}
    current_code = None
    current_name = None
    
    current_raw_text = []
    in_syllabus = False
    in_reference = False
    
    author_blocklist = set()
    
    terminator_re = re.compile(
        r'^(Text\s*Books?|Reference\s*Books?|References|Books?\s*Recommended|Suggested\s*Reading|'
        r'Digital\s*Material|Useful\s*Links|Online\s*Resources|Term\s*Work|Assessment|'
        r'Course\s*Outcomes?|Course\s*Objectives?|Internal\s*Assessment|End\s*Semester\s*Examination)s?:?', 
        re.I
    )
    
    print(f"Processing {pdf_path.name}")
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
                        if current_code and current_code != code:
                            courses[current_code] = (current_code, current_name, current_raw_text)
                        
                        current_code = code
                        current_name = name_part
                        current_raw_text = []
                        in_syllabus = False
                        in_reference = False
                        continue
            
            if current_code:
                if in_syllabus and terminator_re.match(line_str):
                    in_syllabus = False
                    if re.match(r'^(Text\s*Books?|Reference\s*Books?|References|Books?\s*Recommended|Suggested\s*Reading)', line_str, re.I):
                        in_reference = True
                    else:
                        in_reference = False
                elif not in_syllabus and not in_reference and re.match(r'^(\d+\.\d+|[ivx]+\.)', line_str):
                    in_syllabus = True
                    
                if in_syllabus:
                    if line_str and not re.match(r'^\d+$', line_str):
                        current_raw_text.append(line_str)
                elif in_reference:
                    author_blocklist.update(extract_authors(line_str))
                    
    if current_code:
        courses[current_code] = (current_code, current_name, current_raw_text)
        
    print(f"Finished {pdf_path.name}")
    return courses, expected_codes, doc, author_blocklist


def main():
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
    global_author_blocklist = set()
    
    courses_raw = {}
    
    print("Starting processing pdfs...")
    for sem_tag, pdf_name in pdfs:
        pdf_path = pdf_dir / pdf_name
        courses, expected_codes, doc, authors = extract_from_pdf_v5(pdf_path, skip_labs=False)
        docs[pdf_name] = doc
        global_author_blocklist.update(authors)
        for code, (c, n, raw) in courses.items():
            courses_raw[code] = (c, n, raw, pdf_name) # track pdf_name

    print("Finished extracting pdfs, cleaning authors...")
    # Clean up the author blocklist: remove generic words
    clean_authors = []
    for auth in global_author_blocklist:
        if not is_stoplist(auth):
            clean_authors.append((re.compile(r'\b' + re.escape(auth) + r'\b', re.I), auth))
            
    report_dict = {
        'dropped_generic': [],
        'blocklisted_name': [],
        'initials_surname': [],
        'isbn_edition_pub': [],
        'year_19xx_20xx': [],
        'publisher_stoplist': []
    }
    
    all_old_dropped = [] # to compare what was restored
    
    print("Cleaning topics...")
    for code, (c, n, raw, file_name) in courses_raw.items():
        v4_topics = clean_and_split_topics_v5("\n".join(raw), [], {'dropped_generic': [], 'blocklisted_name': [], 'initials_surname': [], 'isbn_edition_pub': [], 'year_19xx_20xx': [], 'publisher_stoplist': []})
        for t in v4_topics:
            if check_person_name(t):
                all_old_dropped.append(t)
        
        topics = clean_and_split_topics_v5("\n".join(raw), clean_authors, report_dict)
        seen = set()
        dedup = []
        for t in topics:
            tl = t.lower()
            if tl not in seen:
                seen.add(tl)
                dedup.append(t)
        
        # Determine true sem
        match = re.search(r'\D(\d)\d{2,3}', code)
        true_sem = f"sem-{match.group(1)}" if match else "unknown"
        
        registry[code] = {'file': file_name, 'true_sem': true_sem, 'course': (c, n, dedup, raw)}

    # Add CSDC7021 explicitly
    doc78 = docs["be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf"]
    for i, page in enumerate(doc78):
        if "CSDC7021" in page.get_text():
            text = page.get_text() + "\n" + (doc78[i+1].get_text() if i+1 < len(doc78) else "")
            lines = text.split('\n')
            in_syllabus = False
            raw_text = []
            terminator_re = re.compile(
                r'^(Text\s*Books?|Reference\s*Books?|References|Books?\s*Recommended|Suggested\s*Reading|'
                r'Digital\s*Material|Useful\s*Links|Online\s*Resources|Term\s*Work|Assessment|'
                r'Course\s*Outcomes?|Course\s*Objectives?|Internal\s*Assessment|End\s*Semester\s*Examination)s?:?', 
                re.I
            )
            for line in lines:
                if in_syllabus and terminator_re.match(line.strip()):
                    break
                if not in_syllabus and re.match(r'^(\d+\.\d+|[ivx]+\.)', line.strip()):
                    in_syllabus = True
                if in_syllabus:
                    raw_text.append(line.strip())
            if raw_text:
                topics = clean_and_split_topics_v5("\n".join(raw_text), clean_authors, report_dict)
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
            
    print("\n=== REFERENCE LEAK FIX ===")
    print(f"Items reaching the filters BEFORE (v4): ~2500 (estimate from previous run)")
    total_raw_topics = sum([len(v['course'][2]) for v in registry.values()]) + sum([len(v) for v in report_dict.values()])
    print(f"Items reaching the filters AFTER (v5): {total_raw_topics}")

    print("\n=== COMPS AUTHOR/PUBLISHER FILTER ===")
    
    for reason, items in report_dict.items():
        # group blocklisted names together to show counts per sub-rule nicely
        if reason.startswith("blocklisted_name"): continue
        print(f"Dropped via {reason}: {len(items)}")
        for it in list(set(items))[:30]:
            print(f"  - {it}")
            
    blocklisted_items = [it for k, v in report_dict.items() if k.startswith("blocklisted_name") for it in v]
    print(f"Dropped via blocklisted_name: {len(blocklisted_items)}")
    for it in list(set(blocklisted_items))[:30]:
        print(f"  - {it}")
            
    # Find restored items
    restored = []
    final_all_topics = []
    for v in registry.values():
        final_all_topics.extend(v['course'][2])
        
    for item in all_old_dropped:
        if item in final_all_topics:
            restored.append(item)
            
    print(f"\nPreviously dropped items RESTORED (no longer dropped by Title Case rule): {len(restored)}")
    for it in list(set(restored))[:30]:
        print(f"  - {it}")
        
    tech_keywords = ['tree', 'network', 'memory', 'algorithm', 'protocol', 'logic', 'graph', 'learning', 'security']
    tech_dropped = []
    for reason, items in report_dict.items():
        for it in items:
            t_lower = it.lower()
            if any(k in t_lower for k in tech_keywords):
                actual_reason = reason.split(" (")[0] if reason.startswith("blocklisted_name") else reason
                tech_dropped.append(f"{it} (Reason: {actual_reason})")
                
    print(f"\nDropped items containing technical keywords (REVIEW): {len(tech_dropped)}")
    for it in set(tech_dropped):
        print(f"  - {it}")


    print("\n=== IT vs COMPS GRANULARITY ===")
    final_ds_path = project_root / "True_Cleaned_Dataset" / "final_training_dataset.csv"
    if final_ds_path.exists():
        df_final = pd.read_csv(final_ds_path)
        it_topics_per_subject = []
        for course, group in df_final.groupby('Course_Code'):
            topics = set(group['concept_a']).union(set(group['concept_b']))
            it_topics_per_subject.append(len(topics))
        
        print(f"IT Extractor Output Path: {final_ds_path}")
        print(f"IT Granularity (Topics per Subject): min={np.min(it_topics_per_subject)}, median={np.median(it_topics_per_subject)}, max={np.max(it_topics_per_subject)}")
        
    comps_counts = [len(v['course'][2]) for k, v in registry.items() if not re.match(r'^(CSL|CSP|CSM|ILO)', k)]
    if comps_counts:
        print(f"COMPS Granularity: min={np.min(comps_counts)}, median={np.median(comps_counts)}, max={np.max(comps_counts)}")


    print("\n=== order_delta and Features ===")
    import joblib
    try:
        model_path = project_root / "models" / "xgb_model.json"
        if model_path.exists():
            import xgboost as xgb
            model = xgb.Booster()
            model.load_model(str(model_path))
            imp = model.get_score(importance_type='gain')
            sorted_imp = sorted(imp.items(), key=lambda x: x[1], reverse=True)
            print("Top 15 Features by Gain:")
            for k, v in sorted_imp[:15]:
                print(f"  {k}: {v:.4f}")
        else:
            print(f"Model not found at {model_path}")
    except Exception as e:
        print(f"Could not load model: {e}")
        
    if final_ds_path.exists():
        it_order_delta = df_final['order_delta'].dropna()
        print("IT order_delta Distribution:")
        print(f"  Min: {it_order_delta.min()}")
        print(f"  p25: {it_order_delta.quantile(0.25)}")
        print(f"  Median: {it_order_delta.median()}")
        print(f"  p75: {it_order_delta.quantile(0.75)}")
        print(f"  Max: {it_order_delta.max()}")
    print("IT Candidate Window: max positional gap of 15 (derived from scripts/pipeline/generate_pairs.py sliding window).")


    print("\n=== REGENERATE CSVs ===")
    out_dir = project_root / "DATA" / "review" / "extraction_pages"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_content_pages = {p: set() for _, p in pdfs}
    page_texts = {}
    for sem_tag, pdf_name in pdfs:
        doc = docs[pdf_name]
        page_texts[pdf_name] = [page.get_text("text").replace('\n', ' ') for page in doc]

    for code, v in registry.items():
        pdf_name = v['file']
        if pdf_name == "unknown": continue
        cached_texts = page_texts[pdf_name]
        for t in v['course'][2]:
            t_sub = t[:20]
            for i, text in enumerate(cached_texts):
                if t_sub in text:
                    pdf_content_pages[pdf_name].add(i)
                    
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
            if pdf_name == "unknown": continue
            doc = docs[pdf_name]
            found_pg = 0
            cached_texts = page_texts[pdf_name]
            for pg in sorted(list(pdf_content_pages[pdf_name])):
                if any(t[:20] in cached_texts[pg] for t in tops):
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
    print("Created extraction_check.csv")

if __name__ == "__main__":
    main()
