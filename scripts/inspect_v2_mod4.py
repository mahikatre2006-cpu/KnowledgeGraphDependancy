import json
with open("DATA/processed/gemini_cache/2113112_v2.json", "r", encoding="utf-8") as f:
    d = json.load(f)
for t in d["topics"]:
    if "counting" in t["unit"].lower() or "module iv" in t["unit"].lower():
        print(t)

