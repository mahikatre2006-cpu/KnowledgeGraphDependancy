import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open("DATA/processed/gemini_cache/64725059d61e07e22ec3672c29b591dcefb4070c545bb7f2041520597c84bc5b.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for t in data["topics"]:
    if any(k in t["name"].lower() for k in ["promise", "fetch", "form", "event", "dom", "flux", "file system", "web module", "generator"]):
        print(t)

