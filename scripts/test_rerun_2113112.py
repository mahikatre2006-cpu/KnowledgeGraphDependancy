import os
import sys
import json
import re
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
import fitz

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

from google import genai

MODEL_NAME = os.environ.get("EXTRACT_MODEL", "gemini-3.8-flash")
API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)

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
    "1. A topic must be a concise, standard technical concept name (1 to 8 words).\n"
    "2. Allow 1-word topics when the word is a standalone concept or list item in its source_quote (e.g. Groups, Rings, Fields, Lattices, Trees). Never invent composite names.\n"
    "3. Topic names must come directly from the original text. Do not invent names or paraphrase.\n"
    "4. Split comma-separated lists of concepts into individual topics (e.g. 'Linear Search, Binary Search' -> 'Linear Search', 'Binary Search').\n"
    "5. Maintain the strict syllabus order (Module 1 through Module 6 in order).\n"
    "6. EXCLUDE: course headers, marks, hours, credits, prerequisite overview headers, course objectives, course outcomes, textbooks, references, authors, publishers, and examination/assessment instructions. Extract ONLY actual technical topics from the modules/units.\n"
    "7. For each topic, provide:\n"
    "   - name: Technical concept name from original text (1 to 8 words)\n"
    "   - unit: Unit/Module name or identifier (e.g. 'Module I: Crisp Set Theory and Logic')\n"
    "   - source_quote: An exact, verbatim substring from the page text where this topic is mentioned (under 200 characters). Ensure that at least 60% of the topic name's words appear verbatim in its source_quote.\n"
    "   - page: The integer page number (1-based, matching the page header) where the source_quote appears.\n"
    "8. Ensure comprehensive coverage across ALL modules (extract 3 to 6 distinct technical topics per module).\n\n"
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

print("Calling Gemini for 2113112...")
response = client.models.generate_content(
    model=MODEL_NAME,
    contents=full_prompt,
    config={
        "response_mime_type": "application/json",
        "temperature": 0.0
    }
)

res_json = json.loads(response.text)
print(f"Extracted {len(res_json.get('topics', []))} topics.")
for t in res_json.get('topics', []):
    print(f"  {t['unit']} | {t['name']} | quote: '{t['source_quote']}' (p. {t['page']})")

with open("DATA/processed/gemini_cache/2113112_rerun.json", "w", encoding="utf-8") as f:
    json.dump(res_json, f, indent=2)

