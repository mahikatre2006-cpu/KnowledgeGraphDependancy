"""
audit_dataset.py
================
Audits labeling_dataset.csv for data contamination without modifying the original.
Flags rows based on:
1. person_name: Two capitalized words / name formats without technical topic nouns.
2. publisher_citation: Publisher names, 'by [Author]', 'Edition', ISBN, quoted book titles.
3. truncated_fragment: Starts or ends with lowercase conjunction/preposition, or unclosed parens.
4. length_bound: < 3 characters or > 15 words.
5. tool_fragment: 'Tools:', bare tool names with no topic context.
6. subject_mismatch: Semantic course mismatch (embeddings) or administrative/exam bleed-in.

Outputs:
  data/label_audit_flagged.csv
  Cleaned_Files/label_audit_flagged.csv
"""

import re
import sys
from pathlib import Path
import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Input paths
DATA_PATH = PROJECT_ROOT / "Cleaned_Files" / "labeling_dataset.csv"
if not DATA_PATH.exists():
    DATA_PATH = PROJECT_ROOT / "data" / "labeling_dataset.csv"

OUT_CSV_DATA = PROJECT_ROOT / "data" / "label_audit_flagged.csv"
OUT_CSV_CLEANED = PROJECT_ROOT / "Cleaned_Files" / "label_audit_flagged.csv"
OUT_CSV_CLEANED = PROJECT_ROOT / "Cleaned_Files" / "audit" / "label_audit_flagged_v3.csv"

# ── 1. Structural & Bibliographic Patterns ────────────────────────────────────

# Well-known technical topic nouns/keywords to prevent flagging legitimate technical terms
TECH_TOPIC_WORDS = {
    'linear', 'algebra', 'fourier', 'series', 'laplace', 'transform', 'operating', 'system',
    'database', 'architecture', 'graph', 'theory', 'machine', 'learning', 'data', 'structures',
    'algorithms', 'compiler', 'design', 'automata', 'theory', 'finite', 'state', 'turing', 'machine',
    'distributed', 'computing', 'cloud', 'blockchain', 'cryptography', 'network', 'security',
    'simplex', 'method', 'matrix', 'matrices', 'eigen', 'values', 'vectors', 'probability',
    'density', 'gradient', 'descent', 'neural', 'networks', 'decision', 'trees', 'random', 'forest',
    'support', 'vector', 'parsing', 'grammar', 'deadlock', 'detection', 'virtual', 'memory',
    'page', 'replacement', 'cache', 'coherence', 'cpu', 'scheduling', 'routing', 'protocols',
    'software', 'engineering', 'agile', 'scrum', 'devops', 'relational', 'model', 'sql', 'queries',
    'normalization', 'concurrency', 'control', 'transaction', 'management', 'indexing', 'hashing',
    'dynamic', 'programming', 'divide', 'conquer', 'greedy', 'backtracking', 'branch', 'bound',
    'big', 'table', 'nosql', 'er', 'eer', 'xml', 'json', 'rest', 'api', 'tcp', 'ip', 'udp',
    'lan', 'wan', 'ethernet', 'switch', 'router', 'arp', 'rarp', 'icmp', 'dhcp', 'dns', 'http',
    'fluid', 'flow', 'solid', 'mixing', 'heat', 'transfer', 'mass', 'separation', 'ergun', 'kynch'
    'fluid', 'flow', 'solid', 'mixing', 'heat', 'transfer', 'mass', 'separation', 'ergun', 'kynch',
    # Specific concepts previously false-positive flagged under person_name
    'block', 'ciphers', 'cipher', 'digital', 'certificates', 'certificate', 'modular', 'arithmetic',
    'normal', 'distribution', 'poisson', 'distributions', 'regular', 'expression', 'expressions',
    'language', 'languages', 'sliding', 'window', 'spring', 'boot', 'time', 'division', 'space',
    'convergence', 'speed', 'search', 'techniques', 'technique', 'statistical', 'text', 'processing',
    'user', 'experience', 'object', 'oriented', 'technology', 'stack', 'functional', 'procedural',
    'logic', 'paradigm', 'event', 'driven', 'mvc', 'pattern', 'controller', 'service', 'restful',
    'cayley', 'hamilton', 'dirichlet', 'conditions', 'markov', 'bayes', 'huffman', 'rsa',
    'kruskal', 'prim', 'dijkstra', 'bellman', 'ford', 'floyd', 'warshall', 'rabin', 'karp', 'kmp'
}

LAB_PROJECT_RE = re.compile(
    r'\b(mini[\s\-]?project|lab\b|laboratory|workshop|capstone|term\s*work)\b', re.I
)

PERSON_NAME_RE = re.compile(
    r'^(Dr\.|Prof\.|Mr\.|Ms\.|Mrs\.)?\s*[A-Z][a-z]+(\s+[A-Z]\.?)?\s+[A-Z][a-z]+$'
)
MULTI_NAME_RE = re.compile(r'([A-Z][a-z]+,\s+){2,}[A-Z]')
AND_AUTHOR_RE = re.compile(r'(&|\band\b)\s+(Dr\.|Prof\.)?\s*[A-Z][a-z]+', re.I)

PUBLISHER_PATS = [
    re.compile(r'\b(McGraw[\s\-]?Hill|Pearson|Wiley|PHI\b|BPB|Springer|Oxford|Cambridge|'
               r'Tata\s*McGraw|Khanna|Narosa|Prentice[\s\-]?Hall|PACKT|Cengage|'
               r'Elsevier|CRC\s*Press|Addison[\s\-]?Wesley|O[\'’]?Reilly|Manning|'
               r'Harper\s*Business|Penguin|Random\s*House|Thomson|Universities\s*Press)\b', re.I),
    re.compile(r'\bby\s+[A-Z][a-z]+(\s+[A-Z]\.?)?\s+[A-Z][a-z]+', re.I),
    re.compile(r'\b\d*(st|nd|rd|th)?\s*Edition\b', re.I),
    re.compile(r'\b(ISBN|Publication|Publishers?|Reprint)\b', re.I),
    re.compile(r'["\u201c\u201d\u2018\u2019\u2015]|[\u2015\u2014]\s*[A-Z]'),
    re.compile(r',\s*[A-Z][a-z]+\s+[A-Z][a-z]+\s*$'),
    re.compile(r'\bet\s+al\b', re.I),
    re.compile(r'\b(NPTEL|W3Schools?|Coursera|edX|GeeksforGeeks|TutorialsPoint)\b', re.I),
    re.compile(r'\b(IIT|NIT|IIIT)\s+[A-Z][a-z]+', re.I),
    re.compile(r'\|\s*(IIT|NIT|IIIT|University)', re.I),
    re.compile(r'\b(dr|prof|mr|ms|mrs)\.\s*[A-Z]', re.I),
    re.compile(r'\b(anish\s*nath|singh\s*rathore|associate\s*dean|forouzan|pressman|tanenbaum|'
               r'korth|silberschatz|galvin|kreyszig|drucker|antonopoulos|gavin\s*wood|imran\s*bashir|'
               r'robert\s*c\.\s*martin|deepak\s*gaikwad|viral\s*thakkar|anderson|schragenheim|'
               r'larman|ashmore|ashwani\s*kumar|ritesh\s*modi|vecchiola|thamaraiselvi|'
               r'chattopadhyay|partha\s*pratim|deisenroth|faisal|cheng\s*soon)\b', re.I),
]

DANGLING_CONJUNCTIONS = {
    'and', 'or', 'of', 'in', 'the', 'with', 'for', 'to', 'from', 'by', 'on', 'at', 'as',
    'that', 'which', 'where', 'when', 'into', 'onto', 'about', 'between', 'through', 'up', 'down',
    'than', 'then', 'etc', 'eg', 'ie', 'vs', 'v', 'versus'
}

TRUNCATED_ENDINGS = re.compile(
    r'\b(periodic|regular|agile|replay|case|various|different|following|above|below|simple|basic|such|'
    r'using|based|including|cold|hot|scheduling|feature|initial|open|self|non|anti|sub|semi|multi|hyper|'
    r'inter|intra|fraud|page|smart|board|special[\s\-]purpose|successful|data|situations|variants|'
    r'challenges|importance|study|methods|terms)\s*$',
    re.I
)

TRUNCATED_STARTS = re.compile(
    r'^(based|including|such\s+as|with|using|between|through|different|various|apps\s*\(pwas\))\b',
    re.I
)

GENERIC_TERMS = {
    'real-time', 'real time', 'operating system', 'operating systems', 'basics', 'introduction',
    'overview', 'summary', 'applications', 'case study', 'case studies', 'types', 'various', 'study',
    'emerging trends', 'self-study topics', 'roles in industry', 'contact hours', '(contact hours)',
    'applications and variants', 'apps (pwas)'
}

TOOL_PATS = [
    re.compile(r'^tools?\s*:\s*', re.I),
    re.compile(r'^(git|github|gitlab|docker|kubernetes|postman|wireshark|selenium|jira|jmeter|linux\s+commands)$', re.I),
    re.compile(r'\b(raspberry\s*pi|thingspeak|blynk|selenium|jira|breadboard|arduino|paho|kotlin|react\s*devtools|simulator)\b', re.I),
]

QUESTION_PATS = [
    re.compile(r'^(Q\d+|Question\s*\d*|Que\.?\s*\d*)\s*[:\.\-]', re.I),
    re.compile(r'^\(\d+\)\s*question', re.I),
]

ADMIN_RUBRIC_PATS = [
    re.compile(r'\b(internal\s*assessment|end\s*sem|term\s*work|question\s*paper|for\s+\d+\s*marks)\b', re.I),
    re.compile(r'\b(internal\s*assessment|end\s*sem|term\s*work|exam|examination|question\s*paper|'
               r'qp\s*setters?|note\s*for\s*qp|module\s*weightage|all\s*cos\s*should|cos?\s*mapped)\b', re.I),
    re.compile(r'\b(letter\s+grades?|grade\s+points?|semester\s+gpa|cgpa|faculty\s+of)\b', re.I),
    re.compile(r'\b(for\s+\d+\s*marks|marks\s*\(attendance\)|\b\d+\s*marks\b|max\.?\s*marks|duration)\b', re.I),
    re.compile(r'\b(suggested\s+list\s+of\s+experiments|list\s+of\s+experiments|journal\s+must|board\s+such\s+as)\b', re.I),
    re.compile(r'\b(students?\s+(are|can|should|shall|must|will|in\s+a\s+group))\b', re.I),
    re.compile(r'\b(solve\s+any|compulsory\s+and\s+should|total\s+of\s+\w+\s+questions|questions?\s+need)\b', re.I),
    re.compile(r'\b(course\s*code|course\s*name|teaching\s*scheme|credits?\s*assigned|contact\s*hours)\b', re.I),
    re.compile(r'^[A-O]\s*\((outstanding|excellent|very\s*good|good|fair|average|pass|fail)\)$', re.I),
    re.compile(r'^course\s*(code|name|objective|outcome)s?:?$', re.I),
    re.compile(r'self[\s\-]study\s*topics?|self[\s\-]learning', re.I),
]

def check_person_name(text: str) -> bool:
    t = text.strip()
    words = [w.lower() for w in re.findall(r'[A-Za-z]+', t)]
    if any(w in TECH_TOPIC_WORDS for w in words):
        return False
    if PERSON_NAME_RE.match(t):
        return True
    if MULTI_NAME_RE.search(t):
        return True
    if AND_AUTHOR_RE.search(t) and len(words) <= 6:
        return True
    return False

def check_publisher_citation(text: str) -> bool:
    t = text.strip()
    for pat in PUBLISHER_PATS:
        if pat.search(t):
            return True
    return False

def check_truncated_fragment(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    if t.lower() in ['special-purpose', 'special purpose', 'time division']:
        return True
    if TRUNCATED_STARTS.search(t):
        return True
    tokens = re.findall(r'[A-Za-z]+', t)
    if not tokens:
        return True
    first_token = tokens[0].lower()
    last_token = tokens[-1].lower()
    if first_token in DANGLING_CONJUNCTIONS and t[0].islower():
        return True
    if last_token in DANGLING_CONJUNCTIONS:
        return True
    if TRUNCATED_ENDINGS.search(t):
        return True
    if re.match(r'^(the|a|an)\s+[A-Z][a-z]+$', t, re.I):
        return True
    if t.count('(') != t.count(')'):
        return True
    if t.count('[') != t.count(']'):
        return True
    if re.search(r'\(.*?\b(proof|only|without|simple)\b', t, re.I):
        return True
    if t.endswith((':', ';', '-', '–', '—', ',', '.')):
        return True
    if re.search(r'\b(ofSquare|realintegrations|andreduction|ofmatrices|intheory)\b', t, re.I):
        return True
    return False

def check_generic_lone_term(text: str) -> bool:
    t = text.strip()
    return t.lower() in GENERIC_TERMS

def check_length_bound(text: str) -> bool:
    t = text.strip()
    if len(t) < 4:
        return True
    words = t.split()
    if len(words) > 7:
        return True
    if t[0].islower():
        return True
    return False

def check_tool_fragment(text: str) -> bool:
    t = text.strip()
    for pat in TOOL_PATS:
        if pat.search(t):
            return True
    return False

def check_admin_rubric(text: str) -> bool:
    t = text.strip()
    for pat in QUESTION_PATS:
        if pat.search(t):
            return True
    for pat in ADMIN_RUBRIC_PATS:
        if pat.search(t):
            return True
    return False

def evaluate_concept(text: str) -> list[str]:
    reasons = []
    if check_length_bound(text):
        reasons.append("length_bound")
    if check_publisher_citation(text):
        reasons.append("publisher_citation")
    if check_person_name(text):
        reasons.append("person_name")
    if check_generic_lone_term(text):
        reasons.append("generic_lone_term")
    if check_tool_fragment(text):
        reasons.append("tool_fragment")
    if check_admin_rubric(text):
        reasons.append("admin_rubric_noise")
    if check_truncated_fragment(text):
        reasons.append("truncated_fragment")
    if check_admin_rubric(text):
        reasons.append("admin_rubric_noise")
    return reasons


def main():
    print(f"Loading dataset from: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    total_rows = len(df)
    print(f"Total rows in dataset: {total_rows}")

    # Load embedding model for semantic course relevance check
    print("Loading all-MiniLM-L6-v2 for semantic subject-alignment check...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")

    # Pre-encode unique concepts and courses
    unique_concepts = list(set(df['concept_a'].dropna().tolist() + df['concept_b'].dropna().tolist()))
    unique_courses = df['course_name'].dropna().unique().tolist()

    print(f"Encoding {len(unique_concepts)} unique concepts and {len(unique_courses)} course names...")
    concept_embs = dict(zip(unique_concepts, model.encode(unique_concepts, normalize_embeddings=True, show_progress_bar=False)))
    course_embs = dict(zip(unique_courses, model.encode(unique_courses, normalize_embeddings=True, show_progress_bar=False)))

    flagged_records = []

    for idx, row in df.iterrows():
        a = str(row['concept_a']) if pd.notna(row['concept_a']) else ""
        b = str(row['concept_b']) if pd.notna(row['concept_b']) else ""
        course = str(row['course_name']) if pd.notna(row['course_name']) else ""

        reasons = []

        # 1. Structural / Bibliographic checks on concept_a
        reasons_a = evaluate_concept(a)
        # 2. Structural / Bibliographic checks on concept_b
        reasons_b = evaluate_concept(b)

        reasons.extend(reasons_a)
        reasons.extend(reasons_b)

        # 3. Semantic Course-Subject Alignment check
        # If the concept has negative or near-zero similarity to its course (and course is known),
        # or if the course itself is an invalid guidelines/lab container
        if course in course_embs:
            c_vec = course_embs[course]
            sim_a = np.dot(concept_embs.get(a, np.zeros(384)), c_vec)
            sim_b = np.dot(concept_embs.get(b, np.zeros(384)), c_vec)

            # Very low semantic relevance (less than 0.04) while not matching general domain keywords
            if sim_a < 0.02 or sim_b < 0.02:
                reasons.append("subject_mismatch")

        # Specific course-level container check (Mini-Project guidelines prose, Lab manual topics)
        if re.search(r'\b(mini[\s\-]?project|lab\b|laboratory|workshop)\b', course, re.I):
            # Check if concepts are project guideline statements rather than core curricular concepts
            if any(term in (a + " " + b).lower() for term in [
                'students shall', 'guide/supervisor', 'log book', 'gantt', 'presentation',
                'rubric', 'marks (attendance)', 'term work marks', 'synopsis'
            ]):
                reasons.append("subject_mismatch")
        # Unconditionally flag all Lab, Mini-Project, Workshop, Capstone, Term work courses
        if LAB_PROJECT_RE.search(course):
            reasons.append("lab_or_project_course")

        if reasons:
            # Deduplicate reasons while preserving order
            unique_reasons = list(dict.fromkeys(reasons))
            primary_reason = unique_reasons[0]
            # If admin_rubric_noise was flagged, map to subject_mismatch or keep
            flagged_row = row.to_dict()
            flagged_row['flag_reason'] = primary_reason
            flagged_row['all_flag_reasons'] = "; ".join(unique_reasons)
            flagged_records.append(flagged_row)

    flagged_df = pd.DataFrame(flagged_records)
    num_flagged = len(flagged_df)
    pct_flagged = (num_flagged / total_rows) * 100

    print("\n" + "=" * 60)
    print("PHASE A: DATASET CONTAMINATION AUDIT SUMMARY")
    print("=" * 60)
    print(f"Total Rows Scanned : {total_rows:,}")
    print(f"Total Rows Flagged : {num_flagged:,}")
    print(f"Percentage Flagged : {pct_flagged:.2f}%")
    print("\nBreakdown by Primary Flag Reason:")
    print("-" * 40)
    if num_flagged > 0:
        counts = flagged_df['flag_reason'].value_counts()
        for reason, count in counts.items():
            print(f"  {reason:<25} : {count:>5} ({count/num_flagged*100:5.1f}%)")
    print("=" * 60)

    # Write output CSVs
    OUT_CSV_DATA.parent.mkdir(parents=True, exist_ok=True)
    # Write output CSV
    OUT_CSV_CLEANED.parent.mkdir(parents=True, exist_ok=True)

    flagged_df.to_csv(OUT_CSV_DATA, index=False)
    flagged_df.to_csv(OUT_CSV_CLEANED, index=False)
    print(f"\nWrote flagged rows to:")
    print(f"  - {OUT_CSV_DATA.relative_to(PROJECT_ROOT)}")
    print(f"  - {OUT_CSV_CLEANED.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()

