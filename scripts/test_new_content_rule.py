import json
import re
from pathlib import Path
import fitz

STOP_WORDS = {'and', 'or', 'in', 'of', 'to', 'for', 'with', 'on', 'at', 'by', 'the', 'a', 'an', 'using', 'vs'}
ACRONYMS = {
    'dom': 'document object model',
    'adt': 'abstract data type',
    'adts': 'abstract data types'
}

def normalize_text_for_match(text: str) -> str:
    if not text:
        return ""
    t = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    t = t.replace('\u2013', '-').replace('\u2014', '-').replace('\u2015', '-')
    t = t.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    t = re.sub(r'\s+', ' ', t)
    return t.strip().lower()

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

def test_subject(cache_path, pdf_path, pages, code):
    doc = fitz.open(pdf_path)
    page_texts = {p: doc[p-1].get_text("text") for p in pages}
    
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"\n==================== Testing {code} with New Rule ====================")
    restored = []
    still_rejected = []
    
    # 8 old rejected in ITC501:
    old_rejected_names = {
        'Document Object Model', 'Promises and Fetch API', 'React Forms and Events',
        'Flux Architecture', 'Node.js File System', 'Node.js Web Module',
        'REST API in Express', 'Express Generator', 'Concept of Abstract Data Types'
    }
    
    for t in data["topics"]:
        name = t["name"]
        quote = t["source_quote"]
        unit = t["unit"]
        page = t["page"]
        
        p_text = page_texts.get(page, "")
        norm_name = normalize_text_for_match(name)
        norm_quote = normalize_text_for_match(quote)
        norm_page = normalize_text_for_match(p_text)
        norm_unit = normalize_text_for_match(unit)
        
        words = re.findall(r'\b[a-z0-9]+\b', norm_name)
        content_words = [w for w in words if w not in STOP_WORDS]
        
        is_acronym = False
        for acr, exp in ACRONYMS.items():
            if re.search(r'\b' + re.escape(acr) + r'\b', norm_quote):
                exp_words = set(re.findall(r'\b[a-z0-9]+\b', exp))
                if all(w in exp_words or w in norm_quote or w in norm_page or w in norm_unit for w in content_words):
                    is_acronym = True
                    break
                    
        word_found_where = {}
        missing = []
        for w in content_words:
            found = []
            if word_in_quote(w, norm_quote):
                found.append("quote")
            if re.search(r'\b' + re.escape(w) + r'\b', norm_page):
                found.append("page_text")
            if re.search(r'\b' + re.escape(w) + r'\b', norm_unit):
                found.append("unit_heading")
                
            if found:
                word_found_where[w] = found
            else:
                if is_acronym:
                    word_found_where[w] = ["acronym_expansion"]
                else:
                    missing.append(w)
                    
        if len(missing) == 0:
            if name in old_rejected_names:
                restored.append((name, is_acronym, word_found_where))
        else:
            still_rejected.append((name, missing))
            
    print(f"Restored topics ({len(restored)}):")
    for r_name, is_acr, locs in restored:
        acr_flag = " [ACRONYM_EXPANDED]" if is_acr else ""
        print(f"  + Restored '{r_name}'{acr_flag}:")
        for w, places in locs.items():
            print(f"      - '{w}': found in {', '.join(places)}")
            
    print(f"Still rejected ({len(still_rejected)}):")
    for s_name, miss in still_rejected:
        print(f"  - '{s_name}': missing content words {miss}")

test_subject(
    "DATA/processed/gemini_cache/64725059d61e07e22ec3672c29b591dcefb4070c545bb7f2041520597c84bc5b.json",
    "DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf",
    [12, 13, 14],
    "ITC501"
)

test_subject(
    "DATA/processed/gemini_cache/6d2eabcf114452ac1817bc4be59ff26451ca258d26b65f168612f4c11692d5bc.json",
    "DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf",
    [13, 14],
    "CSC303"
)

