import re
import fitz
import pandas as pd
from pathlib import Path

# Load dedup map
dedup_df = pd.read_csv("DATA/processed/subject_dedup_map.csv")
dedup_codes = set(dedup_df['sample_code'].str.strip())
dedup_titles = set(dedup_df['norm_title'].str.strip())

def normalize_title(t):
    t = re.sub(r'[\(\)\[\]\{\}\-\–\—\:\,\.\/\'\"]', ' ', t.lower())
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def audit_fe_pdfs():
    fe_files = ["6.22-NIT.pdf", "6.9N-AIML.pdf", "6.14N-CSE-AIML.pdf", "6.28N-DS.pdf"]
    print("=" * 105)
    print("1. IN-SCOPE SEM I & II (FE) PROGRAM STRUCTURE AUDIT")
    print("=" * 105)

    for fname in fe_files:
        matches = list(Path("DATA/raw/2019-scheme").rglob(fname))
        if not matches:
            continue
        path = matches[0]
        doc = fitz.open(path)
        print(f"\nPDF: {fname}")
        print(f"{'Course Code':<14} | {'Course Title':<45} | {'Status':<18} | {'Reason / Notes'}")
        print("-" * 105)
        
        courses = []
        seen = set()
        for p_idx in range(4, min(14, len(doc))):
            text = doc[p_idx].get_text("text")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            for i, l in enumerate(lines):
                m = re.match(r'^([A-Z]{2,5}\s*[0-9]{3,4}[A-Z0-9]?)\b', l)
                if m:
                    code = m.group(1).replace(' ', '')
                    if code in ['REV2019', 'NEP2020', 'TOTAL', 'TABLE', 'CREDIT']:
                        continue
                    if code not in seen:
                        title_parts = []
                        for j in range(i+1, min(i+5, len(lines))):
                            jl = lines[j]
                            if re.match(r'^[0-9\.\-\–\—\*\s]+$', jl):
                                break
                            if re.match(r'^(Course|Code|Theory|Pract|Tut|Credits?|Total|Internal|End|Sem)', jl, re.I):
                                break
                            title_parts.append(jl)
                        title = " ".join(title_parts).strip()
                        if title and len(title) > 2:
                            seen.add(code)
                            courses.append((code, title))
        
        unexplained = []
        for code, title in courses:
            norm_t = normalize_title(title)
            fe_match = dedup_df[(dedup_df['year_tag'] == 'FE') & ((dedup_df['sample_code'] == code) | (dedup_df['norm_title'] == norm_t))]
            branch_match = dedup_df[(dedup_df['year_tag'] != 'FE') & ((dedup_df['sample_code'] == code) | (dedup_df['norm_title'] == norm_t))]
            
            if not fe_match.empty:
                status = "Counted as FE"
                reason = f"Unique FE course ({fe_match.iloc[0]['canonical_name']})"
            elif not branch_match.empty:
                status = "Counted (Branch)"
                reason = f"Branch core theory: {branch_match.iloc[0]['branch']} ({branch_match.iloc[0]['canonical_name']})"
            elif any(sub in code for sub in ['BSL', 'ESL', 'AEL', 'PCL']):
                status = "Excluded"
                reason = "Laboratory course"
            elif any(sub in code for sub in ['BSC102', 'BSC103', 'BSC202', 'BSC203']):
                status = "Excluded"
                reason = "Basic Science (Physics/Chemistry)"
            elif any(sub in code for sub in ['ESC101', 'ESC102', 'ESC201']):
                status = "Excluded"
                reason = "Engineering Science (Mechanics/Electrical/Graphics)"
            elif 'VSEC101' in code or 'VSEC201' in code:
                status = "Excluded"
                reason = "Workshop practice course"
            elif 'VSEC102' in code:
                status = "Excluded"
                reason = "Vocational/skill course"
            else:
                status = "Excluded"
                reason = "Non-computing/Foundation course"
                unexplained.append((code, title))
            
            print(f"{code:<14} | {title[:43]:<45} | {status:<18} | {reason}")
            
        print(f"Uncounted / unexplained theory courses: {len(unexplained)} ({', '.join([c[0] for c in unexplained]) if unexplained else 'None'})\n")

def audit_nep_sem3_4():
    print("=" * 105)
    print("2. NEP-2020 SEM III & IV AUDIT (6.34-N IT AND 6.24-N COMPS)")
    print("=" * 105)
    
    files = [
        ("6.34-N-B.E.-Information-Technology-Sem-III-IV.pdf", "Information Technology"),
        ("6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf", "Computer Engineering")
    ]
    
    for fname, br_name in files:
        matches = list(Path("DATA/raw/2019-scheme").rglob(fname))
        if not matches:
            continue
        path = matches[0]
        doc = fitz.open(path)
        print(f"\nPDF: {fname} ({br_name})")
        print(f"{'Course Code':<14} | {'Course Title':<45} | {'Status':<18} | {'Reason / Notes'}")
        print("-" * 105)
        
        courses = []
        seen = set()
        for p_idx in range(4, min(14, len(doc))):
            text = doc[p_idx].get_text("text")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            for i, l in enumerate(lines):
                # NEP codes: 7 digits
                m = re.match(r'^(\d{7}|[A-Z]{3,5}\d{3,4}[A-Z]?)\b', l)
                if m:
                    code = m.group(1).replace(' ', '')
                    if code in ['REV2019', 'NEP2020', 'TOTAL', 'TABLE', 'CREDIT']:
                        continue
                    if code not in seen:
                        title_parts = []
                        for j in range(i+1, min(i+5, len(lines))):
                            jl = lines[j]
                            if re.match(r'^[0-9\.\-\–\—\*\s]+$', jl):
                                break
                            if re.match(r'^(Course|Code|Theory|Pract|Tut|Credits?|Total|Internal|End|Sem|Department)', jl, re.I):
                                break
                            title_parts.append(jl)
                        title = " ".join(title_parts).strip()
                        if title and len(title) > 2:
                            seen.add(code)
                            courses.append((code, title))
        
        unexplained = []
        for code, title in courses:
            norm_t = normalize_title(title)
            branch_match = dedup_df[((dedup_df['sample_code'] == code) | (dedup_df['norm_title'] == norm_t))]
            
            # Check 5th/6th digit of NEP course code or course type
            # NEP 7-digit pattern: e.g. 2343111 (IT Sem 3 Core Theory), 2343115 (Lab), 2343611 (Skill), 2344411 (Mini Project)
            # 2113111 (COMPS Sem 3 Core Theory), 2113115 (Lab), etc.
            if not branch_match.empty and branch_match.iloc[0]['year_tag'] != 'FE':
                b_row = branch_match.iloc[0]
                status = "Counted (Branch)"
                reason = f"Core Theory: {b_row['canonical_name']}"
            elif code.startswith('299') or 'management' in norm_t or 'environmental' in norm_t or 'ethics' in norm_t:
                status = "Excluded"
                reason = "Non-departmental / Management / Common AEC"
            elif any(title.lower().endswith(x) for x in ['lab', 'laboratory', 'practice']):
                status = "Excluded"
                reason = "Laboratory course"
            elif 'mini project' in norm_t or 'project' in norm_t:
                status = "Excluded"
                reason = "Project course"
            elif 'skill' in norm_t or code.endswith(('611', '612', '613')):
                status = "Excluded"
                reason = "Skill / Vocational course"
            elif 'mdc' in code.lower() or 'minor' in norm_t:
                status = "Excluded"
                reason = "Multidisciplinary / Minor course"
            elif code.endswith(('115', '116', '114')) and ('lab' in norm_t or 'laboratory' in norm_t or 'graphics' in norm_t):
                status = "Excluded"
                reason = "Laboratory course"
            else:
                status = "Excluded"
                reason = "Non-core / Non-theory course"
                unexplained.append((code, title))
                
            print(f"{code:<14} | {title[:43]:<45} | {status:<18} | {reason}")
            
        print(f"Uncounted / unexplained theory courses: {len(unexplained)} ({', '.join([c[0] for c in unexplained]) if unexplained else 'None'})\n")

def audit_it_rev2019():
    print("=" * 105)
    print("3. IT REV-2019 PROGRAM STRUCTURE VS COUNTED CODES (SEM V, VI, VII, VIII)")
    print("=" * 105)
    
    # We inspect 6.12 (Sem V & VI) and Vide-Item-No.-6.23 (Sem VII & VIII)
    f_te = list(Path("DATA/raw/2019-scheme").rglob("6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf"))[0]
    f_be = list(Path("DATA/raw/2019-scheme").rglob("Vide-Item-No.-6.23-R-B.E-information-Technolology-Sem-VII-VIII-CBCS-Rev-2019-C-Scheme..pdf"))[0]
    
    semesters_data = {
        'V': {'pdf': f_te, 'pages': [4, 5, 6]},
        'VI': {'pdf': f_te, 'pages': [7, 8, 9]},
        'VII': {'pdf': f_be, 'pages': [4, 5, 6, 7]},
        'VIII': {'pdf': f_be, 'pages': [8, 9, 10, 11]},
    }
    
    for sem, info in semesters_data.items():
        doc = fitz.open(info['pdf'])
        prog_theory_codes = []
        for p in info['pages']:
            if p >= len(doc):
                continue
            text = doc[p].get_text("text")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            for i, l in enumerate(lines):
                # Matches ITC, ITDO, ILO
                m = re.match(r'^(ITC[5-8]0[1-9]|ITDO[5-8]0[1-9][0-9]?|ILO[7-8]0[1-9][0-9]?)\b', l)
                if m:
                    code = m.group(1)
                    if code not in prog_theory_codes:
                        prog_theory_codes.append(code)
        
        # Counted codes from dedup_map
        # Find which of these codes are counted in dedup_df or ILO
        counted_in_dedup = []
        for c in prog_theory_codes:
            m = dedup_df[dedup_df['sample_code'] == c]
            if not m.empty:
                counted_in_dedup.append((c, m.iloc[0]['canonical_name'], m.iloc[0]['norm_title']))
        
        print(f"\n--- Semester {sem} ---")
        print(f"Theory codes in Program Structure Table ({len(prog_theory_codes)} total):")
        print(f"  {', '.join(prog_theory_codes)}")
        print(f"Counted in deduplicated subjects ({len(counted_in_dedup)} codes):")
        for c, name, norm in counted_in_dedup:
            print(f"  {c:<10} | {name:<40} (norm: {norm})")
        
        missing = [c for c in prog_theory_codes if c not in [x[0] for x in counted_in_dedup]]
        if missing:
            print(f"  Codes not mapped directly by sample_code: {missing}")
            # Check if their title is mapped under another code
            for mc in missing:
                print(f"    Investigating {mc}...")
        else:
            print(f"  All {len(prog_theory_codes)} theory codes accounted for!")

def recompute_budget():
    print("=" * 105)
    print("4. RECOMPUTED API BUDGET (WITHIN-SUBJECT ONLY, NO CROSS-SUBJECT)")
    print("=" * 105)
    # Total extractable subjects = 94
    # Extraction: 94 single pass + ~10 reruns (~10% failure) = 104 calls
    # Labeling: 94 subjects x 2 shuffled passes (within-subject only) = 188 calls
    # Edges estimate per subject: ~25 topics/subject -> ~25-30 candidate edges labeled positive
    # Total single-run edges = 94 * 25 = 2,350 edges
    # Union of run1 and run2 edges = 1.4 * single-run edges = 1.4 * 2,350 = 3,290 edges
    # Verifier batch size = 40 edges per call
    # Verifier calls = 3,290 / 40 = 82.25 -> 83 calls
    # Gemini-direct baseline: 300 gold pairs / 50 per call = 6 calls
    
    n_subj = 94
    extract_calls = n_subj + 10  # 104
    label_calls = n_subj * 2     # 188
    single_run_edges = 2350
    union_edges = int(1.4 * single_run_edges) # 3290
    verifier_calls = (union_edges + 39) // 40 # 83
    baseline_calls = (300 + 49) // 50         # 6
    total_calls = extract_calls + label_calls + verifier_calls + baseline_calls
    
    print(f"Extraction calls:          {extract_calls} (94 subjects + 10 reruns)")
    print(f"Labeling calls (within-subject): {label_calls} (94 subjects x 2 shuffled passes; cross-subject passes dropped)")
    print(f"Estimated single-run edges: {single_run_edges} (~25 positive edges per subject)")
    print(f"Estimated union edges (1.4x): {union_edges}")
    print(f"Verifier calls (40 edges/call): {verifier_calls} ({union_edges} / 40)")
    print(f"Gemini-direct baseline calls: {baseline_calls} (300 pairs / 50 per call)")
    print(f"-" * 45)
    print(f"NEW TOTAL ESTIMATED API CALLS: {total_calls}")

if __name__ == '__main__':
    audit_fe_pdfs()
    audit_nep_sem3_4()
    audit_it_rev2019()
    recompute_budget()

