import json
import re
import fitz
import numpy as np
import pandas as pd
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

REVIEW_DIR = Path("DATA/review")
REVIEW_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------------------------------
# 1. Build the Restored Topics List (12 Topics)
# -------------------------------------------------------------------------------------------------
# 8 from ITC501 (with Promises/Fetch split into 3, and React Forms/Events split into 2)
# 1 from CSC303
restored_only_rows = [
    # ITC501 Module I
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module I: Web programming fundamentals",
        "topic_name": "Document Object Model",
        "source_quote": "DOM",
        "page": 13,
        "human_ok": ""
    },
    # ITC501 Module II (Split from Promises and Fetch API)
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module II: Java script",
        "topic_name": "Promises",
        "source_quote": "Promise",
        "page": 13,
        "human_ok": ""
    },
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module II: Java script",
        "topic_name": "Client-server communication",
        "source_quote": "Client-server \ncommunication",
        "page": 13,
        "human_ok": ""
    },
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module II: Java script",
        "topic_name": "Fetch",
        "source_quote": "Fetch",
        "page": 13,
        "human_ok": ""
    },
    # ITC501 Module III (Split from React Forms and Events)
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module III: React fundamentals",
        "topic_name": "Forms",
        "source_quote": "Forms,",
        "page": 13,
        "human_ok": ""
    },
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module III: React fundamentals",
        "topic_name": "Events",
        "source_quote": "Events,",
        "page": 13,
        "human_ok": ""
    },
    # ITC501 Module IV
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module IV: Advanced React",
        "topic_name": "Flux Architecture",
        "source_quote": "Flux",
        "page": 13,
        "human_ok": ""
    },
    # ITC501 Module V
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module V: Node.js",
        "topic_name": "Node.js File System",
        "source_quote": "File system",
        "page": 13,
        "human_ok": ""
    },
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module V: Node.js",
        "topic_name": "Node.js Web Module",
        "source_quote": "Web module",
        "page": 13,
        "human_ok": ""
    },
    # ITC501 Module VI
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module VI: Express",
        "topic_name": "REST API in Express",
        "source_quote": "REST \nAPI",
        "page": 13,
        "human_ok": ""
    },
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "unit": "Module VI: Express",
        "topic_name": "Express Generator",
        "source_quote": "Generator",
        "page": 13,
        "human_ok": ""
    },
    # CSC303 Module 1
    {
        "course_code": "CSC303",
        "title": "Data Structure",
        "semester": "III",
        "unit": "Module 1: Introduction to Data Structures",
        "topic_name": "Concept of Abstract Data Types",
        "source_quote": "Concept of ADT",
        "page": 13,
        "human_ok": ""
    }
]

df_restored_only = pd.DataFrame(restored_only_rows)
restored_only_path = REVIEW_DIR / "extraction_pilot_restored_only.csv"
df_restored_only.to_csv(restored_only_path, index=False)
print(f"Created '{restored_only_path}' with {len(df_restored_only)} rows.")

# -------------------------------------------------------------------------------------------------
# 2. Build 2113112 Reassessed 54-Topic Collection
# -------------------------------------------------------------------------------------------------
with open("DATA/processed/gemini_cache/2113112_v2.json", "r", encoding="utf-8") as f:
    v2_data = json.load(f)
v2_topics = v2_data["topics"]

dropped_8 = {
    'Universal and Empty Sets',
    'Proof by deduction',
    'Proof by cases',
    'Proof by exhaustion',
    'Poset',
    'Types of Lattices',
    'Sub lattice',
    'Recurrence relations'
}

reassessed_2113112_topics = [t for t in v2_topics if t["name"] not in dropped_8]
assert len(reassessed_2113112_topics) == 54

reassessed_2113112_rows = []
for t in reassessed_2113112_topics:
    reassessed_2113112_rows.append({
        "course_code": "2113112",
        "title": "Discrete Structures and Graph Theory",
        "semester": "III",
        "unit": t["unit"],
        "topic_name": t["name"],
        "source_quote": t["source_quote"],
        "page": t["page"],
        "human_ok": ""
    })

df_2113112_reassessed = pd.DataFrame(reassessed_2113112_rows)
path_2113112_reassessed = REVIEW_DIR / "extraction_pilot_2113112_reassessed.csv"
df_2113112_reassessed.to_csv(path_2113112_reassessed, index=False)
print(f"Created '{path_2113112_reassessed}' with {len(df_2113112_reassessed)} rows.")

# -------------------------------------------------------------------------------------------------
# 3. Build Full Corrected Master Topic Collection (110 Rows Total)
# -------------------------------------------------------------------------------------------------
# Course 1: ITC501 (34 topics: 31 original with 2 merged topics replaced by 5 split topics)
with open("DATA/processed/gemini_cache/64725059d61e07e22ec3672c29b591dcefb4070c545bb7f2041520597c84bc5b.json", "r", encoding="utf-8") as f:
    itc_raw = json.load(f)["topics"]

itc_master_rows = []
for t in itc_raw:
    name = t["name"]
    if name == "Promises and Fetch API":
        # Split into 3
        itc_master_rows.append({
            "course_code": "ITC501", "title": "Internet Programming", "semester": "V",
            "unit": "Module II: Java script", "topic_name": "Promises",
            "source_quote": "Promise", "page": 13, "human_ok": ""
        })
        itc_master_rows.append({
            "course_code": "ITC501", "title": "Internet Programming", "semester": "V",
            "unit": "Module II: Java script", "topic_name": "Client-server communication",
            "source_quote": "Client-server \ncommunication", "page": 13, "human_ok": ""
        })
        itc_master_rows.append({
            "course_code": "ITC501", "title": "Internet Programming", "semester": "V",
            "unit": "Module II: Java script", "topic_name": "Fetch",
            "source_quote": "Fetch", "page": 13, "human_ok": ""
        })
    elif name == "React Forms and Events":
        # Split into 2
        itc_master_rows.append({
            "course_code": "ITC501", "title": "Internet Programming", "semester": "V",
            "unit": "Module III: React fundamentals", "topic_name": "Forms",
            "source_quote": "Forms,", "page": 13, "human_ok": ""
        })
        itc_master_rows.append({
            "course_code": "ITC501", "title": "Internet Programming", "semester": "V",
            "unit": "Module III: React fundamentals", "topic_name": "Events",
            "source_quote": "Events,", "page": 13, "human_ok": ""
        })
    else:
        itc_master_rows.append({
            "course_code": "ITC501", "title": "Internet Programming", "semester": "V",
            "unit": t["unit"], "topic_name": t["name"],
            "source_quote": t["source_quote"], "page": t["page"], "human_ok": ""
        })

print(f"ITC501 master rows count: {len(itc_master_rows)}")
assert len(itc_master_rows) == 34

# Course 2: CSC303 (22 topics)
with open("DATA/processed/gemini_cache/6d2eabcf114452ac1817bc4be59ff26451ca258d26b65f168612f4c11692d5bc.json", "r", encoding="utf-8") as f:
    csc_raw = json.load(f)["topics"]

csc_master_rows = []
for t in csc_raw:
    csc_master_rows.append({
        "course_code": "CSC303", "title": "Data Structure", "semester": "III",
        "unit": t["unit"], "topic_name": t["name"],
        "source_quote": t["source_quote"], "page": t["page"], "human_ok": ""
    })

print(f"CSC303 master rows count: {len(csc_master_rows)}")
assert len(csc_master_rows) == 22

# Course 3: 2113112 (54 topics)
master_all_rows = itc_master_rows + csc_master_rows + reassessed_2113112_rows
df_master = pd.DataFrame(master_all_rows)
master_path = REVIEW_DIR / "extraction_pilot_master_corrected.csv"
df_master.to_csv(master_path, index=False)
print(f"Created '{master_path}' with {len(df_master)} total rows.")
assert len(df_master) == 110

