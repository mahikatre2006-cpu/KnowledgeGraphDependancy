"""
scripts/phase1_manifest_triage.py
==================================
Phase 1: Manifest triage & subject deduplication for Mumbai University Rev-2019 / NEP-2020.
Generates:
  - DATA/processed/manifest_classified.csv
  - DATA/processed/subject_dedup_map.csv
"""

import sys
import csv
import re
from pathlib import Path
import fitz

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "DATA" / "raw" / "scheme_manifest.csv"
OUT_DIR = PROJECT_ROOT / "DATA" / "processed"

EXCLUDED_PROGRAMMES = [
    "Chemical Engineering",
    "Civil Engineering",
    "Electrical Engineering",
    "Electrical & Computer Engineering",
    "Electronics and Telecommunication Engineering",
    "Mechanical Engineering",
    "Mechanical and Automation Engineering"
]

SKIP_NAME_RE = re.compile(
    r'\b(mini[\s\-]?project|capstone|lab\b|laboratory|workshop|'
    r'term\s*work|practical|oral|project\s*[1-2A-B]|project\s*stage|major\s*project|seminar|internship)\b',
    re.I
)
SKIP_CODE_RE = re.compile(
    r'\b([A-Z]{2,3}L[0-9]{3}|[A-Z]{2,3}M[0-9]{3}|PCL[0-9]{3}|BSL[0-9]{3}|ESL[0-9]{3}|PEL[0-9]{3})\b',
    re.I
)

def get_branch_canonical(prog: str) -> str:
    p = prog.lower()
    if "information technology" in p:
        return "IT"
    elif "computer science engineering" in p or "computer science & engineering" in p:
        if "artificial intelligence" in p or "machine learning" in p or "data science" in p:
            return "AIML family"
        return "CSE"
    elif "computer engineering" in p:
        return "COMPS"
    elif any(x in p for x in ["artificial intelligence", "machine learning", "data science", "ai", "ds"]):
        return "AIML family"
    return "OTHER"

def normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r'[\u2010-\u2015\-\–\—]', ' ', t)
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def parse_pdf_subjects(pdf_path: Path):
    doc = fitz.open(str(pdf_path))
    subjects = []
    for p_idx in range(len(doc)):
        text = doc[p_idx].get_text("text")
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        top_lines = lines[:15]
        top_text = " ".join(top_lines).lower()
        if "course code" in top_text or ("course" in top_text and "code" in top_text and ("teaching scheme" in top_text or "credits" in top_text)):
            code = None
            name = None
            for i, l in enumerate(lines[:25]):
                m = re.fullmatch(r'([A-Z]{2,5}[0-9]{3,4}[A-Z]?|\d{7})', l)
                if m:
                    cand = m.group(1)
                    if cand not in ['2019', '2020', '2021', '2022', '2023', '2024', '2025', '2026', 'REV2019', 'NEP2020']:
                        code = cand
                        code_idx = i
                        name_parts = []
                        for j in range(code_idx + 1, min(code_idx + 8, len(lines))):
                            jl = lines[j]
                            if re.match(r'^[0-9\.\-\–\—\*\s]+$', jl):
                                break
                            if re.match(r'^(Course|Code|Teaching|Credits?|Theory|Pract|Tut|Examination)', jl, re.I):
                                break
                            name_parts.append(jl)
                        if name_parts:
                            name = " ".join(name_parts)
                        break
            if not code or not name:
                for i, l in enumerate(lines):
                    if re.match(r'^Course\s*Code\b', l, re.I):
                        for j in range(i+1, min(i+10, len(lines))):
                            m = re.search(r'\b([A-Z]{3,5}\s*[0-9]{3,4}[A-Z]?)\b', lines[j])
                            if m:
                                cand = m.group(1).replace(' ', '')
                                if not SKIP_CODE_RE.search(cand):
                                    code = cand
                                    if j + 1 < len(lines) and len(lines[j+1]) > 3:
                                        name = lines[j+1]
                                    break
                        if code and name:
                            break
            if code and name:
                name = re.sub(r'\s+', ' ', name).strip()
                if not SKIP_NAME_RE.search(name) and not SKIP_CODE_RE.search(code):
                    if not any(s['code'] == code for s in subjects):
                        subjects.append({
                            "code": code,
                            "name": name,
                            "page": p_idx + 1
                        })
    return subjects

def run_triage():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
        manifest_rows = list(csv.DictReader(f))

    total_manifest = len(manifest_rows)
    classified_rows = []
    in_scope_rows = []
    excluded_count = 0

    for r in manifest_rows:
        prog = r['programme']
        is_excluded = any(ex.lower() in prog.lower() for ex in EXCLUDED_PROGRAMMES)
        sem = r['semesters']
        sch = r['scheme']
        b_canon = get_branch_canonical(prog)

        if is_excluded:
            role = "excluded"
            year_tag = "EXCLUDED"
            excluded_count += 1
        elif sem == "Sem. I & II":
            role = "train_only"
            year_tag = "FE"
            in_scope_rows.append(r)
        elif b_canon in ["IT", "COMPS", "CSE"]:
            role = "train_val_test"
            if "III" in sem or "IV" in sem:
                year_tag = "SE"
            elif "V" in sem or "VI" in sem:
                year_tag = "TE"
            elif "VII" in sem or "VIII" in sem:
                year_tag = "BE"
            else:
                year_tag = "SE_PLUS"
            in_scope_rows.append(r)
        else:
            role = "train_only"
            if "III" in sem or "IV" in sem:
                year_tag = "SE"
            elif "V" in sem or "VI" in sem:
                year_tag = "TE"
            elif "VII" in sem or "VIII" in sem:
                year_tag = "BE"
            else:
                year_tag = "SE_PLUS"
            in_scope_rows.append(r)

        row_copy = dict(r)
        row_copy['role'] = role
        row_copy['year_tag'] = year_tag
        row_copy['branch_canonical'] = b_canon
        classified_rows.append(row_copy)

    # Write manifest_classified.csv
    manifest_out = OUT_DIR / "manifest_classified.csv"
    with open(manifest_out, 'w', newline='', encoding='utf-8') as f:
        fieldnames = list(classified_rows[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(classified_rows)

    # Scan subjects
    raw_subjects = []
    for r in in_scope_rows:
        p = PROJECT_ROOT / r['path']
        subs = parse_pdf_subjects(p)
        prog = r['programme']
        branch = get_branch_canonical(prog)
        is_fe = (r['semesters'] == 'Sem. I & II')
        for s in subs:
            raw_subjects.append({
                "code": s['code'],
                "name": s['name'],
                "norm_title": normalize_title(s['name']),
                "pdf": p.name,
                "path": r['path'],
                "programme": prog,
                "branch": "FE" if is_fe else branch,
                "original_branch": branch,
                "scheme": r['scheme'],
                "semesters": r['semesters'],
                "is_fe": is_fe,
                "page": s['page']
            })

    # COMPS Sem 3 vs Sem 4 deduplication
    comps_sem4_codes = {s['code'] for s in raw_subjects if s['pdf'] == 'be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf'}
    sem3_overlap = [s for s in raw_subjects if s['pdf'] == 'be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf' and s['code'] in comps_sem4_codes]
    overlap_codes = {s['code'] for s in sem3_overlap}

    deduped_courses = []
    for s in raw_subjects:
        if s['pdf'] == 'be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf':
            if s['code'] in overlap_codes:
                continue
        deduped_courses.append(s)

    # Subject dedup map: unique normalized title mapping
    # Ensure each normalized subject title is unique
    title_map = {}
    for s in deduped_courses:
        nt = s['norm_title']
        if nt not in title_map:
            # Determine role: FE is train_only, AIML family is train_only, IT/COMPS/CSE is train_val_test
            if s['is_fe']:
                role = "train_only"
            elif s['branch'] in ["IT", "COMPS", "CSE"]:
                role = "train_val_test"
            else:
                role = "train_only"

            title_map[nt] = {
                "norm_title": nt,
                "canonical_name": s['name'],
                "sample_code": s['code'],
                "branch": s['branch'],
                "scheme": s['scheme'],
                "semesters": s['semesters'],
                "year_tag": "FE" if s['is_fe'] else ("SE" if ("III" in s['semesters'] or "IV" in s['semesters']) else ("TE" if ("V" in s['semesters'] or "VI" in s['semesters']) else "BE")),
                "role": role,
                "source_pdf": s['pdf']
            }

    subject_out = OUT_DIR / "subject_dedup_map.csv"
    with open(subject_out, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ["norm_title", "canonical_name", "sample_code", "branch", "scheme", "semesters", "year_tag", "role", "source_pdf"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for nt in sorted(title_map.keys()):
            writer.writerow(title_map[nt])

    # Compute metrics
    in_scope_count = len(in_scope_rows)
    fe_subjects = {s['norm_title'] for s in deduped_courses if s['is_fe']}
    non_fe = [s for s in deduped_courses if not s['is_fe']]

    branch_counts = {
        "IT": len({s['norm_title'] for s in non_fe if s['branch'] == 'IT'}),
        "COMPS": len({s['norm_title'] for s in non_fe if s['branch'] == 'COMPS'}),
        "CSE": len({s['norm_title'] for s in non_fe if s['branch'] == 'CSE'}),
        "AIML family": len({s['norm_title'] for s in non_fe if s['branch'] == 'AIML family'})
    }

    scheme_counts = {
        "Rev-2019": len({s['norm_title'] for s in deduped_courses if s['scheme'] == 'Rev-2019'}),
        "NEP-2020": len({s['norm_title'] for s in deduped_courses if s['scheme'] == 'NEP-2020'})
    }

    print("==================================================")
    print("PHASE 1 MANIFEST TRIAGE & DEDUPLICATION REPORT")
    print("==================================================")
    print(f"Total manifest entries:      {total_manifest}")
    print(f"Excluded PDFs:              {excluded_count} (Chemical, Civil, Electrical, Electrical & Computer, EXTC, Mechanical, Mech & Auto)")
    print(f"In-scope PDFs:              {in_scope_count} (Plan said ~28; real manifest is 27 total - 8 excluded = 19)")
    print(f"COMPS Sem 3/4 deduped:       {len(overlap_codes)} courses ({sorted(list(overlap_codes))})")
    print(f"FE unique subjects:          {len(fe_subjects)}")
    print(f"\nDeduplicated subjects per branch (Sem III+):")
    print(f"  IT:                       {branch_counts['IT']}")
    print(f"  COMPS:                    {branch_counts['COMPS']}")
    print(f"  CSE:                      {branch_counts['CSE']}")
    print(f"  AIML family:              {branch_counts['AIML family']}")
    print(f"\nDeduplicated subjects per scheme (including FE):")
    print(f"  Rev-2019:                 {scheme_counts['Rev-2019']}")
    print(f"  NEP-2020:                 {scheme_counts['NEP-2020']}")
    print(f"\nTotal deduplicated subjects across all in-scope PDFs: {len(title_map)}")
    print("==================================================")

if __name__ == "__main__":
    run_triage()

