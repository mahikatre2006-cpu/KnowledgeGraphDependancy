import json

with open("DATA/processed/gemini_cache/2113112_v2.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for i, t in enumerate(data["topics"]):
    print(f"{i+1:2d}. [{t['unit']}] {t['name']}")

