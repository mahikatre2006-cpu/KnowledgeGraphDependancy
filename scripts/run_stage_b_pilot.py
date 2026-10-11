import os
import sys
import json
import re
import hashlib
from pathlib import Path
import pandas as pd
import fitz
from dotenv import load_dotenv

# Ensure stdout handles UTF-8 on Windows
sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

from google import genai

# Setup directories
CACHE_DIR = Path("DATA/processed/gemini_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REVIEW_DIR = Path("DATA/review")
REVIEW_DIR.mkdir(parents=True, exist_ok=True)

# Model configuration
MODEL_NAME = os.environ.get("EXTRACT_MODEL", "gemini-3.8-flash")
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable is not set!")

client = genai.Client(api_key=API_KEY)

# Normalization function
def normalize_text_for_match(text: str) -> str:
    if not text:
        return ""
    # 1. dehyphenate line-break hyphens: "inter-\nactive" -> "interactive"
    t = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    # 2. replace unicode dashes/quotes
    t = t.replace('\u2013', '-').replace('\u2014', '-').replace('\u2015', '-')
    t = t.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    # 3. collapse whitespace and newlines to a single space
    t = re.sub(r'\s+', ' ', t)
    # 4. strip and lowercase
    return t.strip().lower()

def extract_pdf_page_texts(pdf_path: str, pages: list):
    doc = fitz.open(pdf_path)
    page_texts = {}
    for p in pages:
        # p is 1-based PDF page number
        if 1 <= p <= len(doc):
            page_texts[p] = doc[p-1].get_text("text")
    return page_texts

def build_prompt(course_code: str, title: str, semester: str, page_texts: dict) -> tuple:
    prompt_instructions = (
        f"You are extracting curriculum topics for the Mumbai University engineering course:\n"
        f"Course Code: {course_code}\n"
        f"Course Title: {title}\n"
        f"Semester: {semester}\n\n"
        f"RULES FOR EXTRACTION:\n"
        f"1. A topic must be a concise, meaningful technical concept name (2 to 8 words).\n"
        f"2. Split comma-separated lists of concepts into individual topics (e.g. 'Linear Search, Binary Search' -> 'Linear Search', 'Binary Search').\n"
        f"3. Merge trivial or fragmented sub-points into standard technical terms.\n"
        f"4. Maintain the strict syllabus order (Module 1 through Module 6 in order).\n"
        f"5. EXCLUDE: course headers, marks, hours, credits, prerequisite overview headers, course objectives, course outcomes, textbooks, references, authors, publishers, and examination/assessment instructions. Extract ONLY actual technical topics from the modules/units.\n"
        f"6. For each topic, provide:\n"
        f"   - name: Short concept name (2 to 8 words)\n"
        f"   - unit: Unit/Module name or identifier (e.g. 'Module 1: Crisp Set Theory')\n"
        f"   - source_quote: An exact, verbatim substring from the page text where this topic is mentioned. Do NOT edit, paraphrase, or invent words.\n"
        f"   - page: The integer page number (1-based, matching the page header) where the source_quote appears.\n"
        f"7. Target approximately 3 to 6 distinct topics per module (roughly 20 to 35 topics total for the subject).\n\n"
        f"Output strictly valid JSON with this exact schema:\n"
        f"{{\n"
        f'  "course_code": "{course_code}",\n'
        f'  "title": "{title}",\n'
        f'  "semester": "{semester}",\n'
        f'  "topics": [\n'
        f'    {{\n'
        f'      "name": "Concept Name",\n'
        f'      "unit": "Module 1",\n'
        f'      "source_quote": "exact verbatim text from page",\n'
        f'      "page": 13\n'
        f'    }}\n'
        f'  ]\n'
        f"}}"
    )
    
    syllabus_content_parts = []
    for p, text in sorted(page_texts.items()):
        syllabus_content_parts.append(f"--- Page {p} ---\n{text}")
    input_text = "\n\n".join(syllabus_content_parts)
    
    return prompt_instructions, input_text

def call_gemini_with_cache(prompt_instructions: str, input_text: str):
    full_prompt = f"{prompt_instructions}\n\nSYLLABUS CONTENT:\n{input_text}"
    content_hash = hashlib.sha256(f"{MODEL_NAME}_{prompt_instructions}_{input_text}".encode('utf-8')).hexdigest()
    cache_path = CACHE_DIR / f"{content_hash}.json"
    
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data, True
    
    # Call Gemini API
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
        # Fallback regex if markdown blocks included
        m = re.search(r'\{.*\}', response.text, re.DOTALL)
        if m:
            data = json.loads(m.group(0))
        else:
            raise e
            
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    return data, False

def validate_topics(raw_topics: list, page_texts: dict):
    accepted = []
    rejected = []
    seen_names = set()
    
    normalized_pages = {p: normalize_text_for_match(text) for p, text in page_texts.items()}
    
    banned_words = [
        'mark', 'marks', 'credit', 'credits', 'hour', 'hours', 'textbook', 'text book',
        'reference', 'syllabus', 'course outcome', 'assessment', 'prerequisite',
        'co mapping', 'internal assessment', 'term work', 'duration'
    ]
    
    for t in raw_topics:
        name = t.get("name", "").strip()
        unit = t.get("unit", "").strip()
        quote = t.get("source_quote", "").strip()
        page = t.get("page")
        
        words = name.split()
        norm_name = name.lower()
        
        # 1. Check quote presence on reported page
        if not quote:
            rejected.append((t, "empty_source_quote"))
            continue
            
        norm_quote = normalize_text_for_match(quote)
        
        # Check reported page
        matched_page = None
        if page in normalized_pages and norm_quote in normalized_pages[page]:
            matched_page = page
        else:
            # Check other pages of this subject in case of slight off-by-one in page reporting
            for p, p_text in normalized_pages.items():
                if norm_quote in p_text:
                    matched_page = p
                    break
                    
        if not matched_page:
            rejected.append((t, f"source_quote_not_found_on_page_{page}"))
            continue
            
        # 2. Word count check (2 to 8 words)
        if len(words) < 2 or len(words) > 8:
            rejected.append((t, f"word_count_out_of_bounds ({len(words)} words)"))
            continue
            
        # 3. Duplicate check
        if norm_name in seen_names:
            rejected.append((t, f"duplicate_topic: '{name}'"))
            continue
            
        # 4. Non-ASCII / garbage check
        if not re.match(r'^[a-zA-Z0-9\s\-\/\(\)\.\,\&\+\#\:\']+$', name):
            rejected.append((t, f"non_ascii_or_special_chars: '{name}'"))
            continue
            
        # 5. Banned administrative words check
        has_banned = False
        for bw in banned_words:
            if re.search(r'\b' + re.escape(bw) + r'\b', norm_name):
                rejected.append((t, f"contains_banned_word: '{bw}'"))
                has_banned = True
                break
        if has_banned:
            continue
            
        # Topic passed all checks
        seen_names.add(norm_name)
        accepted.append({
            "name": name,
            "unit": unit,
            "source_quote": quote,
            "page": matched_page
        })
        
    return accepted, rejected

def run_pilot():
    pilot_subjects = [
        {
            "branch_scheme": "IT Rev-2019",
            "course_code": "ITC501",
            "title": "Internet Programming",
            "semester": "V",
            "pdf": "DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf",
            "pages": [12, 13, 14]
        },
        {
            "branch_scheme": "COMPS Rev-2019",
            "course_code": "CSC303",
            "title": "Data Structure",
            "semester": "III",
            "pdf": "DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf",
            "pages": [13, 14]
        },
        {
            "branch_scheme": "NEP-2020",
            "course_code": "2113112",
            "title": "Discrete Structures and Graph Theory",
            "semester": "III",
            "pdf": "DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf",
            "pages": [19, 20, 21]
        }
    ]
    
    all_pilot_rows = []
    
    print("=" * 95)
    print("STAGE B: 3-SUBJECT PILOT EXTRACTION REPORT")
    print(f"Model: {MODEL_NAME} | Temperature: 0.0")
    print("=" * 95)
    
    for subj in pilot_subjects:
        print(f"\n>>> Subject: {subj['course_code']} - {subj['title']} ({subj['branch_scheme']}, Sem {subj['semester']})")
        print(f"    PDF: {subj['pdf']} | Pages: {subj['pages']}")
        
        page_texts = extract_pdf_page_texts(subj['pdf'], subj['pages'])
        prompt_inst, input_text = build_prompt(subj['course_code'], subj['title'], subj['semester'], page_texts)
        
        data, is_cache = call_gemini_with_cache(prompt_inst, input_text)
        req_used = 0 if is_cache else 1
        
        raw_topics = data.get("topics", [])
        accepted, rejected = validate_topics(raw_topics, page_texts)
        
        quote_passed = len([t for t in raw_topics if t.get("source_quote") and any(normalize_text_for_match(t["source_quote"]) in normalize_text_for_match(txt) for txt in page_texts.values())])
        quote_pass_rate = (quote_passed / len(raw_topics) * 100) if raw_topics else 0.0
        
        print(f"    Raw topics extracted:   {len(raw_topics)}")
        print(f"    Quote pass rate:        {quote_pass_rate:.1f}% ({quote_passed}/{len(raw_topics)})")
        print(f"    Rejected topics:        {len(rejected)}")
        if rejected:
            for r_top, reason in rejected:
                print(f"      * Rejected '{r_top.get('name')}': {reason}")
        print(f"    Final accepted count:   {len(accepted)}")
        print(f"    Requests used:          {req_used} (Cache hit: {is_cache})")
        
        # Verify quality gates
        gate_ok = (8 <= len(accepted) <= 60)
        print(f"    Quality Gate [8-60 topics]: {'PASS' if gate_ok else 'FAIL'} ({len(accepted)} topics)")
        
        # Add to CSV rows
        for t in accepted:
            all_pilot_rows.append({
                "course_code": subj["course_code"],
                "title": subj["title"],
                "semester": subj["semester"],
                "unit": t["unit"],
                "topic_name": t["name"],
                "source_quote": t["source_quote"],
                "page": t["page"],
                "human_ok": ""  # Explicitly blank as required
            })
            
    # Write DATA/review/extraction_pilot.csv
    pilot_df = pd.DataFrame(all_pilot_rows)
    csv_path = REVIEW_DIR / "extraction_pilot.csv"
    pilot_df.to_csv(csv_path, index=False)
    print("\n" + "=" * 95)
    print(f"Pilot review file written to: {csv_path} (Total rows: {len(pilot_df)})")
    print(f"human_ok column left blank: {pilot_df['human_ok'].isna().all() or (pilot_df['human_ok'] == '').all()}")
    print("=" * 95)

if __name__ == "__main__":
    run_pilot()

