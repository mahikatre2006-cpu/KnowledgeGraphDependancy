import json
import re
import numpy as np
import fitz

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

def audit_cached_subject(cache_path, pdf_path, pages, code_name):
    print(f"\n==================== Auditing {code_name} ====================")
    with open(cache_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    doc = fitz.open(pdf_path)
    page_texts = {p: doc[p-1].get_text("text") for p in pages}
    norm_pages = {p: normalize_text_for_match(txt) for p, txt in page_texts.items()}
    
    raw_topics = data.get("topics", [])
    print(f"Raw topics in cache: {len(raw_topics)}")
    
    accepted = []
    rejected = []
    name_not_in_quote = []
    quote_lens = []
    seen = set()
    
    banned = ['mark', 'marks', 'credit', 'credits', 'hour', 'hours', 'textbook', 'reference', 'syllabus', 'assessment']
    
    for t in raw_topics:
        name = t.get("name", "").strip()
        quote = t.get("source_quote", "").strip()
        unit = t.get("unit", "").strip()
        page = t.get("page")
        
        words = name.split()
        norm_name = normalize_text_for_match(name)
        norm_quote = normalize_text_for_match(quote)
        quote_lens.append(len(quote))
        
        # 1. Quote check
        if not quote:
            rejected.append((name, "empty_source_quote"))
            continue
        if len(quote) > 200:
            rejected.append((name, f"quote_length_exceeds_200_chars ({len(quote)} chars)"))
            continue
            
        # Match quote in page
        matched_page = None
        if page in norm_pages and norm_quote in norm_pages[page]:
            matched_page = page
        else:
            for p, p_text in norm_pages.items():
                if norm_quote in p_text:
                    matched_page = p
                    break
        if not matched_page:
            rejected.append((name, f"quote_not_found_on_page_{page}"))
            continue
            
        # Word overlap >= 60%
        topic_words = re.findall(r'\b[a-z0-9]+\b', norm_name)
        if topic_words:
            matched_w = [w for w in topic_words if word_in_quote(w, norm_quote)]
            pct = len(matched_w) / len(topic_words)
            if pct < 0.60:
                rejected.append((name, f"words_in_quote_below_60_percent ({len(matched_w)}/{len(topic_words)} = {pct*100:.1f}%)"))
                continue
                
        # Length check
        if len(words) < 1 or len(words) > 8:
            rejected.append((name, f"word_count_out_of_bounds ({len(words)} words)"))
            continue
            
        # Duplicate
        if norm_name in seen:
            rejected.append((name, f"duplicate_topic: {name}"))
            continue
            
        # Banned
        if any(re.search(r'\b' + re.escape(b) + r'\b', norm_name) for b in banned):
            rejected.append((name, "banned_words"))
            continue
            
        seen.add(norm_name)
        accepted.append(t)
        
        # Name check: test whether normalized topic name occurs inside normalized quote
        if norm_name not in norm_quote:
            name_not_in_quote.append((name, quote, matched_page))
            
    print(f"Accepted topics: {len(accepted)}")
    print(f"Rejected topics: {len(rejected)}")
    for r_name, r_reason in rejected:
        print(f"  * Rejected '{r_name}': {r_reason}")
        
    q_arr = np.array(quote_lens)
    print(f"Quote stats: Median={np.median(q_arr):.1f}, P95={np.percentile(q_arr, 95):.1f}, Max={np.max(q_arr):.1f}")
    
    print(f"NAME_NOT_IN_QUOTE: {len(name_not_in_quote)} topics")
    for n, q, p in name_not_in_quote:
        print(f"  * Name: '{n}' | Quote: '{q}' (p. {p})")
        
    return accepted, rejected, name_not_in_quote

audit_cached_subject(
    "DATA/processed/gemini_cache/64725059d61e07e22ec3672c29b591dcefb4070c545bb7f2041520597c84bc5b.json",
    "DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf",
    [12, 13, 14],
    "ITC501 (Internet Programming)"
)

audit_cached_subject(
    "DATA/processed/gemini_cache/6d2eabcf114452ac1817bc4be59ff26451ca258d26b65f168612f4c11692d5bc.json",
    "DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf",
    [13, 14],
    "CSC303 (Data Structure)"
)

