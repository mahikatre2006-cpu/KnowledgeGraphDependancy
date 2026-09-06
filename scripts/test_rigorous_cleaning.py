import pandas as pd
import re

df = pd.read_csv('Cleaned_Files/labeling_dataset.csv')
print(f"Total rows in labeling_dataset.csv: {len(df)}")

# 1. Reject lab/project/workshop courses
LAB_PROJECT_RE = re.compile(
    r'\b(mini[\s\-]?project|lab\b|laboratory|workshop|capstone|term\s*work)\b', re.I
)

# 2. Bibliographic & citation patterns
CITATION_RE = re.compile(
    r'(\b(mcgraw|pearson|wiley|phi\b|bpb|springer|narosa|khanna|prentice|cengage|'
    r'elsevier|addison|oreilly|manning|harper|penguin|random\s*house|thomson|universities\s*press)\b|'
    r'\b(nptel|w3schools?|coursera|edx|geeksforgeeks|tutorialspoint)\b|'
    r'\b(text\s*books?|references?|online\s*ref|website\s*name|isbn|publication|publishers?|reprint)\b|'
    r'\b\d*(st|nd|rd|th)?\s*edition\b|'
    r'\bby\s+[A-Z][a-z]+|'
    r'["\u201c\u201d\u2018\u2019\u2015]|'
    r'\b(dr|prof|mr|ms|mrs)\.\s*[A-Z]|'
    r'\b(anish\s*nath|singh\s*rathore|associate\s*dean|forouzan|pressman|tanenbaum|'
    r'korth|silberschatz|galvin|kreyszig|drucker|antonopoulos|gavin\s*wood|imran\s*bashir|'
    r'robert\s*c\.\s*martin|deepak\s*gaikwad|viral\s*thakkar|anderson|schragenheim|'
    r'larman|ashmore|ashwani\s*kumar|ritesh\s*modi|vecchiola|thamaraiselvi|'
    r'chattopadhyay|partha\s*pratim|deisenroth|faisal|cheng\s*soon)\b|'
    r'([A-Z][a-z]+,\s+){2,}[A-Z]|'
    r',\s*[A-Z][a-z]+\s+[A-Z][a-z]+\s*$)',
    re.I
)

# 3. Administrative, Exam, and Rubric patterns
ADMIN_EXAM_RE = re.compile(
    r'(\b(internal\s*assessment|end\s*sem|term\s*work|exam|examination|question\s*paper|'
    r'qp\s*setters?|note\s*for\s*qp|module\s*weightage|all\s*cos\s*should|cos?\s*mapped)\b|'
    r'\b(letter\s+grades?|grade\s+points?|semester\s+gpa|cgpa|faculty\s+of)\b|'
    r'\b(for\s+\d+\s*marks|marks\s*\(attendance\)|\b\d+\s*marks\b|max\.?\s*marks|duration)\b|'
    r'\b(suggested\s+list\s+of\s+experiments|list\s+of\s+experiments|journal\s+must|board\s+such\s+as)\b|'
    r'\b(students?\s+(are|can|should|shall|must|will|in\s+a\s+group))\b|'
    r'\b(solve\s+any|compulsory\s+and\s+should|total\s+of\s+\w+\s+questions|questions?\s+need)\b|'
    r'\bpart\s*\([a-z]\)\s*and\s*part\s*\([a-z]\)\b|'
    r'\bno\s+questions\s+will\s+be\s+asked\b|'
    r'\b(course\s*code|course\s*name|teaching\s*scheme|credits?\s*assigned)\b|'
    r'^[a-o]\s*\((outstanding|excellent|very\s*good|good|fair|average|pass|fail)\)$|'
    r'^q\d+[:.]|'
    r'^\(\d+\)\s*question)',
    re.I
)

# 4. Fragment, punctuation, and prose patterns
DANGLING_CONJUNCTIONS = {
    'and', 'or', 'of', 'in', 'the', 'with', 'for', 'to', 'from', 'by', 'on', 'at', 'as',
    'that', 'which', 'where', 'when', 'into', 'onto', 'about', 'between', 'through', 'up', 'down'
}

def is_concept_invalid(text: str) -> tuple[bool, str]:
    t = str(text).strip()
    if not t or len(t) < 4:
        return True, "length_too_short"
    words = t.split()
    if len(words) > 8:
        return True, "word_count_gt_8"
    if t[0].islower():
        return True, "starts_with_lowercase"
    
    # Check start/end conjunctions & prefixes
    tokens = re.findall(r'[A-Za-z]+', t)
    if not tokens:
        return True, "no_alpha_tokens"
    if tokens[0].lower() in DANGLING_CONJUNCTIONS and t[0].islower():
        return True, "starts_with_conjunction"
    if tokens[-1].lower() in DANGLING_CONJUNCTIONS:
        return True, "ends_with_conjunction"
    if re.search(r'\b(open|self|the|a|an|non|anti|sub|semi|multi|hyper|inter|intra|different|various)\s*$', t, re.I):
        return True, "ends_with_dangling_word"
    if re.match(r'^(the|a|an)\s+[A-Z][a-z]+$', t, re.I):
        return True, "bare_article_noun_fragment"
    
    # Check parens balance: strictly equal number of '(' and ')'
    if t.count('(') != t.count(')'):
        return True, "unbalanced_parens"
    if t.count('[') != t.count(']'):
        return True, "unbalanced_brackets"
    if re.search(r'\(.*?\b(proof|only|without|simple)\b', t, re.I):
        return True, "proof_instruction_paren"
    if t.endswith((':', ';', '-', '–', '—', ',', '.')):
        return True, "trailing_punctuation"
    
    # Check citations and admin regexes
    if CITATION_RE.search(t):
        return True, "citation_author_publisher"
    if ADMIN_EXAM_RE.search(t):
        return True, "admin_exam_rubric"
    
    # Clean syllabus prefixes like "Self-learning Topics:" if present
    if re.search(r'self[\s\-]learning', t, re.I):
        return True, "self_learning_header"
        
    return False, ""

clean_rows = []
flagged_rows = []

for idx, r in df.iterrows():
    course = str(r['course_name']).strip()
    a = str(r['concept_a']).strip()
    b = str(r['concept_b']).strip()
    
    # Step 1: Course level filter
    if LAB_PROJECT_RE.search(course):
        flagged_rows.append((idx, r, "lab_or_project_course"))
        continue
    
    # Step 2: Concept A filter
    inv_a, reason_a = is_concept_invalid(a)
    if inv_a:
        flagged_rows.append((idx, r, f"concept_a_{reason_a}"))
        continue
        
    # Step 3: Concept B filter
    inv_b, reason_b = is_concept_invalid(b)
    if inv_b:
        flagged_rows.append((idx, r, f"concept_b_{reason_b}"))
        continue
        
    clean_rows.append((idx, r))

print(f"\n=======================================================")
print(f"RIGOROUS FILTER RESULTS:")
print(f"=======================================================")
print(f"Total Rows Scanned : {len(df):,}")
print(f"Total Rows Flagged : {len(flagged_rows):,} ({len(flagged_rows)/len(df)*100:.1f}%)")
print(f"Total Clean Rows   : {len(clean_rows):,} ({len(clean_rows)/len(df)*100:.1f}%)")

clean_df = pd.DataFrame([r for _, r in clean_rows])
pos = (clean_df['label'] == 1).sum()
neg = (clean_df['label'] == 0).sum()
print(f"\nClean Rows Label Balance:")
print(f"  Positive (1): {pos:,} ({pos/len(clean_df)*100:.1f}%)")
print(f"  Negative (0): {neg:,} ({neg/len(clean_df)*100:.1f}%)")
print(f"\nClean Rows Course Distribution:")
print(clean_df['course_name'].value_counts())

with open('scripts/rigorous_clean_samples.txt', 'w', encoding='utf-8') as f:
    for _, r in clean_df.iterrows():
        f.write(f"[{r['course_name']}] '{r['concept_a']}' -> '{r['concept_b']}' (Label: {r['label']})\n")

print("\nWrote all clean rows to scripts/rigorous_clean_samples.txt for verification.")
