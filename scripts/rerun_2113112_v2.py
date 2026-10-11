import os
import sys
import json
import re
import numpy as np
from pathlib import Path
import pandas as pd
import fitz
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

from google import genai

MODEL_NAME = os.environ.get("EXTRACT_MODEL", "gemini-3.8-flash")
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

REVIEW_DIR = Path("DATA/review")
REVIEW_DIR.mkdir(parents=True, exist_ok=True)
TOPICS_DIR = Path("DATA/processed/topics")
TOPICS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = Path("DATA/processed/gemini_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

pdf_path = "DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf"
pages = [19, 20, 21]

doc = fitz.open(pdf_path)
page_texts = {p: doc[p-1].get_text("text") for p in pages}

prompt_instructions = (
    "You are extracting curriculum topics for the Mumbai University engineering course:\n"
    "Course Code: 2113112\n"
    "Course Title: Discrete Structures and Graph Theory\n"
    "Semester: III\n\n"
    "RULES FOR EXTRACTION:\n"
    "1. Topic names must come directly from the original text (1 to 8 words). Never invent names, acronym expansions, or composite titles not in the text.\n"
    "2. Allow 1-word topics when the word is a standalone concept or list item in its source_quote (e.g. Groups, Rings, Fields, Lattices, Trees).\n"
    "3. Enumerations joined by commas or 'and' MUST be split into separate individual topics. For example, in Module III: 'Types: Injective, Surjective, and Bijective Functions. Composition, Inverse Functions' must be split into: 'Injective Functions', 'Surjective Functions', 'Bijective Functions', 'Composition', 'Inverse Functions'.\n"
    "4. Maintain the strict syllabus order (Module I through Module VI in order).\n"
    "5. EXCLUDE: Prerequisite section (Module 0), Self-learning topics, course headers, marks, hours, credits, course objectives, course outcomes, textbooks, references, authors, and examination/assessment instructions. Extract ONLY actual technical topics taught in the core module content.\n"
    "6. For each topic, provide:\n"
    "   - name: Exact technical concept name from the text (1 to 8 words)\n"
    "   - unit: Unit/Module name or identifier (e.g. 'Module III: Functions')\n"
    "   - source_quote: An exact, verbatim substring from the page text where this topic is mentioned (under 200 characters). Ensure that the source_quote directly contains the topic name and its words.\n"
    "   - page: The integer page number (1-based) where the source_quote appears.\n"
    "7. Ensure balanced coverage across all modules (at least 3 to 6 distinct technical topics per module).\n\n"
    "Output strictly valid JSON with this exact schema:\n"
    "{\n"
    '  "course_code": "2113112",\n'
    '  "title": "Discrete Structures and Graph Theory",\n'
    '  "semester": "III",\n'
    '  "topics": [\n'
    '    {\n'
    '      "name": "Concept Name",\n'
    '      "unit": "Module I: Crisp Set Theory and Logic",\n'
    '      "source_quote": "exact verbatim text from page",\n'
    '      "page": 20\n'
    '    }\n'
    '  ]\n'
    "}"
)

syllabus_content_parts = []
for p, text in sorted(page_texts.items()):
    syllabus_content_parts.append(f"--- Page {p} ---\n{text}")
input_text = "\n\n".join(syllabus_content_parts)
full_prompt = f"{prompt_instructions}\n\nSYLLABUS CONTENT:\n{input_text}"

print("Calling Gemini API for 2113112 (v2 re-run)...")
response = client.models.generate_content(
    model=MODEL_NAME,
    contents=full_prompt,
    config={
        "response_mime_type": "application/json",
        "temperature": 0.0
    }
)

res_json = json.loads(response.text)
with open("DATA/processed/gemini_cache/2113112_v2.json", "w", encoding="utf-8") as f:
    json.dump(res_json, f, indent=2)

print(f"Extracted {len(res_json.get('topics', []))} raw topics.")

