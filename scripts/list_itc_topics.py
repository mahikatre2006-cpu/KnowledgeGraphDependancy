import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("DATA/processed/gemini_cache/64725059d61e07e22ec3672c29b591dcefb4070c545bb7f2041520597c84bc5b.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for idx, t in enumerate(data["topics"], 1):
    print(f"{idx:>2}. [{t['unit']}] '{t['name']}' | quote: '{t['source_quote']}' | page: {t['page']}")

