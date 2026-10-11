import json
import re
import numpy as np

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
    # plural / singular
    if w.endswith('s') and len(w) > 3 and re.search(r'\b' + re.escape(w[:-1]) + r'\b', norm_quote):
        return True
    if w.endswith('es') and len(w) > 4 and re.search(r'\b' + re.escape(w[:-2]) + r'\b', norm_quote):
        return True
    # compound word (e.g. semigroups -> semi group)
    cw = re.sub(r'[^a-z0-9]', '', w)
    cq = re.sub(r'[^a-z0-9]', '', norm_quote)
    if cw in cq or (len(cw) > 3 and cw[:-1] in cq):
        return True
    return False

with open("DATA/processed/gemini_cache/257ca70b7c2c58a2070c025a92525688482177de66531f034f4e3bb2ba5d4c74.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total topics: {len(data['topics'])}")
quote_lengths = []
for t in data["topics"]:
    name = t["name"]
    quote = t["source_quote"]
    norm_name = normalize_text_for_match(name)
    norm_quote = normalize_text_for_match(quote)
    quote_lengths.append(len(quote))
    
    # Extract words
    words = [w for w in re.findall(r'\b[a-z0-9]+\b', norm_name)]
    # filter stop words like 'and', 'of', 'in' if desired or keep all
    matching = [w for w in words if word_in_quote(w, norm_quote)]
    pct = (len(matching) / len(words)) if words else 0.0
    status = "PASS" if pct >= 0.60 and len(quote) <= 200 else "FAIL"
    print(f"[{status}] {name:<35} | quote_len={len(quote):<3} | words: {len(matching)}/{len(words)} ({pct*100:.1f}%) | matching: {matching}")

q_arr = np.array(quote_lengths)
print("\n--- Quote Length Stats ---")
print(f"Median: {np.median(q_arr):.1f}")
print(f"P95:    {np.percentile(q_arr, 95):.1f}")
print(f"Max:    {np.max(q_arr):.1f}")

