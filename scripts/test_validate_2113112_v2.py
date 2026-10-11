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

with open("DATA/processed/gemini_cache/2113112_v2.json", "r", encoding="utf-8") as f:
    data = json.load(f)

doc = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf")
pages = {p: doc[p-1].get_text("text") for p in [19, 20, 21]}
norm_pages = {p: normalize_text_for_match(txt) for p, txt in pages.items()}

banned = ['mark', 'marks', 'credit', 'credits', 'hour', 'hours', 'textbook', 'reference', 'syllabus', 'assessment', 'prerequisite']

accepted = []
rejected = []
name_not_in_quote = []
seen = set()

for t in data["topics"]:
    name = t.get("name", "").strip()
    quote = t.get("source_quote", "").strip()
    page = t.get("page")
    
    words = name.split()
    norm_name = normalize_text_for_match(name)
    norm_quote = normalize_text_for_match(quote)
    
    # 1. Quote check
    if not quote:
        rejected.append((name, "empty_quote"))
        continue
    if len(quote) > 200:
        rejected.append((name, f"quote_length_exceeds_200_chars ({len(quote)} chars)"))
        continue
    matched_page = None
    if page in norm_pages and norm_quote in norm_pages[page]:
        matched_page = page
    else:
        for p, p_txt in norm_pages.items():
            if norm_quote in p_txt:
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
            
    # Word count
    if len(words) < 1 or len(words) > 8:
        rejected.append((name, f"word_count_out_of_bounds ({len(words)} words)"))
        continue
        
    # Duplicate
    if norm_name in seen:
        rejected.append((name, f"duplicate_topic: {name}"))
        continue
        
    # Non-ascii
    if not re.match(r'^[a-zA-Z0-9\s\-\/\(\)\.\,\&\+\#\:\'’‘“”–—]+$', name):
        rejected.append((name, f"non_ascii_or_special: {name}"))
        continue
        
    # Banned
    if any(re.search(r'\b' + re.escape(b) + r'\b', norm_name) for b in banned):
        rejected.append((name, "banned_words"))
        continue
        
    seen.add(norm_name)
    accepted.append({
        "name": name,
        "unit": t.get("unit"),
        "source_quote": quote,
        "page": matched_page
    })
    
    if norm_name not in norm_quote:
        name_not_in_quote.append((name, quote, matched_page))

print(f"Total raw: {len(data['topics'])}")
print(f"Accepted: {len(accepted)}")
print(f"Rejected: {len(rejected)}")
for r, reason in rejected:
    print(f"  * Rejected '{r}': {reason}")
    
print(f"\nNAME_NOT_IN_QUOTE: {len(name_not_in_quote)}")
for n, q, p in name_not_in_quote:
    print(f"  * Name: '{n}' | Quote: '{q}' (p. {p})")

