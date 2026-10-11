import os
import sys
import json
import re
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import fitz
from dotenv import load_dotenv

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

from google import genai

CACHE_DIR = Path("DATA/processed/gemini_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REVIEW_DIR = Path("DATA/review")
REVIEW_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = os.environ.get("EXTRACT_MODEL", "gemini-2.5-flash")
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set!")

client = genai.Client(api_key=API_KEY)

# -------------------------------------------------------------------------------------------------
# Normalization & Matching Utilities
# -------------------------------------------------------------------------------------------------
def normalize_text_for_match(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    t = t.replace('\u2013', '-').replace('\u2014', '-').replace('\u2015', '-')
    t = t.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    t = re.sub(r'\s+', ' ', t)
    return t.strip().lower()

def extract_pdf_page_texts(pdf_path: str, pages: list) -> dict:
    doc = fitz.open(pdf_path)
    page_texts = {}
    for p in pages:
        if 1 <= p <= len(doc):
            page_texts[p] = doc[p-1].get_text("text")
    return page_texts

# -------------------------------------------------------------------------------------------------
# Revised Prompt Construction
# -------------------------------------------------------------------------------------------------
def build_revised_prompt(course_code: str, title: str, semester: str, page_texts: dict) -> tuple:
    prompt_instructions = (
        f"You are extracting curriculum topics for the Mumbai University engineering course:\n"
        f"Course Code: {course_code}\n"
        f"Course Title: {title}\n"
        f"Semester: {semester}\n\n"
        f"CRITICAL EXTRACTION RULES:\n"
        f"1. ATOMICITY (ONE TOPIC PER INDEPENDENT CONCEPT):\n"
        f"   Extract exactly ONE topic per independently listed syllabus concept. Do NOT combine distinct concepts into compound or merged topic names.\n\n"
        f"2. MANDATORY SPLITTING OF ENUMERATIONS & COORDINATED CONCEPTS:\n"
        f"   Whenever the syllabus lists multiple concepts separated by commas, slashes, or coordinating conjunctions ('and', 'or', 'vs'), you MUST split them into separate individual topics.\n"
        f"   - Split comma-separated items: 'Linear Search, Binary Search' -> 'Linear Search', 'Binary Search'.\n"
        f"   - Split coordinated protocols/technologies: 'HTTP protocol, HTTPS' -> 'HTTP Protocol', 'HTTPS'. 'DNS, TLS' -> 'DNS', 'TLS'.\n"
        f"   - Split data structures/types: 'Circular Linked List, Doubly Linked List' -> 'Circular Linked List', 'Doubly Linked List'.\n"
        f"   - Split algorithms: 'Depth First Search (DFS) and Breadth First Search (BFS)' -> 'Depth First Search', 'Breadth First Search'.\n"
        f"   - Split asynchronous/API concepts: 'Promise, Client-server communication, Fetch' -> 'Promises', 'Client-server communication', 'Fetch'.\n"
        f"   - Split React concepts: 'Components, Component lifecycle' -> 'Components', 'Component Lifecycle'. 'State and Props' -> 'State', 'Props'. 'Forms, Events' -> 'Forms', 'Events'.\n"
        f"   - Split Node/Express concepts: 'Buffers, Streams' -> 'Buffers', 'Streams'. 'Authentication, sessions' -> 'Authentication', 'Sessions'.\n"
        f"   - Split mathematical/graph entities: 'Walk, Path, Circuit' -> 'Walk', 'Path', 'Circuit'. 'Connected Graphs, Disconnected Graph' -> 'Connected Graphs', 'Disconnected Graph'. 'Semi group, Monoid' -> 'Semigroup', 'Monoid'. 'Groups, Subgroups, Abelian Group, and Cyclic group' -> 'Groups', 'Subgroups', 'Abelian Group', 'Cyclic Group'.\n\n"
        f"3. PRESERVE GENUINE UMBRELLA TOPICS:\n"
        f"   If an overarching category or heading introduces a section (e.g. 'Operations on Data Structures' or 'Types of Graphs'), you may retain the umbrella concept, but you MUST also extract the individual sub-concepts enumerated under it.\n\n"
        f"4. ZERO UNSUPPORTED PHRASING OR EXPANSIONS:\n"
        f"   Never invent words or speculative expansions not supported by the syllabus text or module title. For example, if the syllabus mentions 'REST API', do NOT invent 'REST API Architecture'. If the syllabus mentions 'Equivalence Classes', do NOT invent 'Equivalence Relations and Classes'.\n\n"
        f"5. TOPIC LENGTH & WORD COUNT:\n"
        f"   A topic name should be concise: 1 to 6 words (max 8 words). Concise 1-word concepts (e.g., 'Ring', 'Monoid', 'Walk', 'Path', 'Circuit', 'Promises', 'Fetch', 'Forms', 'Events', 'Buffers', 'Streams') are fully permitted when they represent distinct technical entities.\n\n"
        f"6. SOURCE GROUNDING & PROVENANCE:\n"
        f"   For every extracted topic, provide:\n"
        f"   - name: Short, atomic technical concept name (1 to 6 words).\n"
        f"   - unit: Exact Unit/Module name (e.g. 'Module I: Web programming fundamentals').\n"
        f"   - source_quote: An exact, character-for-character VERBATIM substring copied directly from the page text where this topic is mentioned. Do NOT edit, paraphrase, or invent words.\n"
        f"   - page: The integer 1-based page number where the source_quote appears.\n\n"
        f"7. COVERAGE TARGETS:\n"
        f"   Extract all valid technical concepts from Module 1 through Module 6 in syllabus order. Every module must have at least 3 topics. Overall subject count must be between 8 and 60 topics.\n\n"
        f"8. STRICT EXCLUSIONS:\n"
        f"   EXCLUDE course overview headers, prerequisite overviews, marks, hours, credits, course objectives, course outcomes, textbooks, references, authors, publishers, term work, and exam instructions.\n\n"
        f"Output strictly valid JSON with this exact schema:\n"
        f"{{\n"
        f'  "course_code": "{course_code}",\n'
        f'  "title": "{title}",\n'
        f'  "semester": "{semester}",\n'
        f'  "topics": [\n'
        f'    {{\n'
        f'      "name": "Atomic Concept Name",\n'
        f'      "unit": "Module Name",\n'
        f'      "source_quote": "exact verbatim text from page",\n'
        f'      "page": 13\n'
        f'    }}\n'
        f'  ]\n'
        f"}}"
    )
    
    syllabus_parts = []
    for p, text in sorted(page_texts.items()):
        syllabus_parts.append(f"--- Page {p} ---\n{text}")
    input_text = "\n\n".join(syllabus_parts)
    
    return prompt_instructions, input_text

# -------------------------------------------------------------------------------------------------
# Fresh API Call Execution (Exactly 1 call per subject)
# -------------------------------------------------------------------------------------------------
def call_fresh_gemini(prompt_instructions: str, input_text: str, course_code: str):
    full_prompt = f"{prompt_instructions}\n\nSYLLABUS CONTENT:\n{input_text}"
    print(f"Calling Gemini API ({MODEL_NAME}) for {course_code}...")
    
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=full_prompt,
        config={
            "response_mime_type": "application/json",
            "temperature": 0.0
        }
    )
    
    try:
        data = json.loads(response.text)
    except Exception as e:
        m = re.search(r'\{.*\}', response.text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
        else:
            raise e
            
    # Save raw fresh output to cache
    fresh_cache_path = CACHE_DIR / f"{course_code}_v2_fresh.json"
    with open(fresh_cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved fresh response to '{fresh_cache_path}'.")
    return data

# -------------------------------------------------------------------------------------------------
# Topic Validation Pipeline
# -------------------------------------------------------------------------------------------------
STOP_WORDS = {'and', 'or', 'in', 'of', 'to', 'for', 'with', 'on', 'at', 'by', 'the', 'a', 'an', 'using', 'vs'}
ACRONYMS = {
    'dom': 'document object model',
    'adt': 'abstract data type',
    'adts': 'abstract data types',
    'dfs': 'depth first search',
    'bfs': 'breadth first search',
    'rest': 'representational state transfer',
    'repl': 'read eval print loop',
    'spa': 'single page applications',
    'spas': 'single page applications'
}

def word_in_quote(w: str, norm_quote: str) -> bool:
    if re.search(r'\b' + re.escape(w) + r'\b', norm_quote):
        return True
    if w.endswith('s') and len(w) > 3 and re.search(r'\b' + re.escape(w[:-1]) + r'\b', norm_quote):
        return True
    if w.endswith('es') and len(w) > 4 and re.search(r'\b' + re.escape(w[:-2]) + r'\b', norm_quote):
        return True
    cw = re.sub(r'[^a-z0-9]', '', w)
    cq = re.sub(r'[^a-z0-9]', '', norm_quote)
    if cw in cq or (len(cw) > 3 and cw[:-1] in cq):
        return True
    return False

def validate_extracted_topics(raw_topics: list, page_texts: dict):
    accepted = []
    rejected = []
    seen_names = set()
    norm_pages = {p: normalize_text_for_match(txt) for p, txt in page_texts.items()}
    banned = ['mark', 'marks', 'credit', 'credits', 'hour', 'hours', 'textbook', 'reference', 'syllabus', 'assessment', 'prerequisite']
    
    for t in raw_topics:
        name = t.get("name", "").strip()
        unit = t.get("unit", "").strip()
        quote = t.get("source_quote", "").strip()
        page = t.get("page")
        
        words = name.split()
        norm_name = normalize_text_for_match(name)
        norm_quote = normalize_text_for_match(quote)
        
        # 1. Quote check
        if not quote:
            rejected.append((t, "empty_source_quote"))
            continue
        if len(quote) > 200:
            rejected.append((t, f"quote_length_exceeds_200_chars ({len(quote)})"))
            continue
            
        matched_page = None
        if page in norm_pages and norm_quote in norm_pages[page]:
            matched_page = page
        else:
            for p, p_text in norm_pages.items():
                if norm_quote in p_text:
                    matched_page = p
                    break
        if not matched_page:
            rejected.append((t, f"source_quote_not_found_on_page_{page}"))
            continue
            
        # 2. Word count check (1 to 8 words)
        if len(words) < 1 or len(words) > 8:
            rejected.append((t, f"word_count_out_of_bounds ({len(words)})"))
            continue
            
        # 3. Duplicate check
        if norm_name in seen_names:
            rejected.append((t, f"duplicate_topic: '{name}'"))
            continue
            
        # 4. Banned words check
        if any(re.search(r'\b' + re.escape(b) + r'\b', norm_name) for b in banned):
            rejected.append((t, f"contains_banned_word"))
            continue
            
        # 5. Unsupported phrasing / Content word check
        c_words = [w for w in re.findall(r'\b[a-z0-9]+\b', norm_name) if w not in STOP_WORDS]
        p_text = norm_pages.get(matched_page, "")
        norm_unit = normalize_text_for_match(unit)
        
        # Check acronym
        is_acr = False
        for acr, exp in ACRONYMS.items():
            if re.search(r'\b' + re.escape(acr) + r'\b', norm_quote):
                exp_words = set(re.findall(r'\b[a-z0-9]+\b', exp))
                if all(w in exp_words or w in norm_quote or w in p_text or w in norm_unit for w in c_words):
                    is_acr = True
                    break
                    
        missing_words = []
        for w in c_words:
            if not (word_in_quote(w, norm_quote) or re.search(r'\b' + re.escape(w) + r'\b', p_text) or re.search(r'\b' + re.escape(w) + r'\b', norm_unit) or is_acr):
                missing_words.append(w)
                
        if missing_words:
            rejected.append((t, f"unsupported_phrasing_missing_words: {missing_words}"))
            continue
            
        seen_names.add(norm_name)
        accepted.append({
            "name": name,
            "unit": unit,
            "source_quote": quote,
            "page": matched_page
        })
        
    return accepted, rejected

# -------------------------------------------------------------------------------------------------
# Main Pilot v2 Runner
# -------------------------------------------------------------------------------------------------
def run_fresh_pilot():
    print("=" * 105)
    print("STAGE B FRESH PILOT EXTRACTION (EXACTLY 3 FRESH API CALLS)")
    print("=" * 105)
    
    pilot_subjects = [
        {
            "course_code": "ITC501",
            "title": "Internet Programming",
            "semester": "V",
            "pdf": "DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf",
            "pages": [12, 13, 14]
        },
        {
            "course_code": "CSC303",
            "title": "Data Structure",
            "semester": "III",
            "pdf": "DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf",
            "pages": [13, 14]
        },
        {
            "course_code": "2113112",
            "title": "Discrete Structures and Graph Theory",
            "semester": "III",
            "pdf": "DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf",
            "pages": [19, 20, 21]
        }
    ]
    
    api_calls_count = 0
    all_v2_rows = []
    subject_results = {}
    
    for subj in pilot_subjects:
        c_code = subj["course_code"]
        print(f"\n>>> Running Fresh Extraction for {c_code} ({subj['title']})...")
        
        page_texts = extract_pdf_page_texts(subj["pdf"], subj["pages"])
        prompt_inst, input_text = build_revised_prompt(c_code, subj["title"], subj["semester"], page_texts)
        
        # Fresh API Call
        data = call_fresh_gemini(prompt_inst, input_text, c_code)
        api_calls_count += 1
        
        raw_topics = data.get("topics", [])
        accepted, rejected = validate_extracted_topics(raw_topics, page_texts)
        
        subject_results[c_code] = {
            "title": subj["title"],
            "raw_count": len(raw_topics),
            "accepted": accepted,
            "rejected": rejected
        }
        
        print(f"    Raw topics extracted : {len(raw_topics)}")
        print(f"    Accepted topics      : {len(accepted)}")
        print(f"    Rejected topics      : {len(rejected)}")
        if rejected:
            for r_t, r_reason in rejected:
                print(f"      * Rejected '{r_t.get('name')}': {r_reason}")
                
        # Build CSV rows (human_ok strictly blank)
        for t in accepted:
            all_v2_rows.append({
                "course_code": c_code,
                "title": subj["title"],
                "semester": subj["semester"],
                "unit": t["unit"],
                "topic_name": t["name"],
                "source_quote": t["source_quote"],
                "page": t["page"],
                "human_ok": ""  # Strictly blank
            })
            
    print(f"\nTotal Fresh API Calls Made: {api_calls_count} (Permitted: 3)")
    assert api_calls_count == 3, f"Expected exactly 3 API calls, got {api_calls_count}"
    
    # Write DATA/review/extraction_pilot_v2.csv
    v2_df = pd.DataFrame(all_v2_rows)
    v2_path = REVIEW_DIR / "extraction_pilot_v2.csv"
    v2_df.to_csv(v2_path, index=False)
    print(f"\nSuccessfully wrote {len(v2_df)} rows to '{v2_path}'.")
    print(f"Verified all human_ok cells are blank: {bool((v2_df['human_ok'] == '').all())}")
    
    return subject_results, v2_df

if __name__ == "__main__":
    run_fresh_pilot()

