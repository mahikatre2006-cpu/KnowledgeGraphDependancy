import os
import json

cache_dir = "DATA/processed/gemini_cache"
for f in os.listdir(cache_dir):
    if f.endswith(".json"):
        p = os.path.join(cache_dir, f)
        try:
            with open(p, "r", encoding="utf-8") as jf:
                data = json.load(jf)
                code = data.get("course_code")
                title = data.get("title")
                topics = data.get("topics", [])
                print(f"File: {f}")
                print(f"  course_code: {code}")
                print(f"  title:       {title}")
                print(f"  topics count:{len(topics)}")
        except Exception as e:
            print(f"File: {f} -> Error: {e}")

