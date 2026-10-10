import json
import time
import re
import csv
import os
from pathlib import Path
import fitz

import google.generativeai as genai
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "DATA"
REBUILD_DIR = DATA_DIR / "rebuild"
NEW_ROWS_CSV = REBUILD_DIR / "m1_new_rows.csv"
REPORT_CSV = REBUILD_DIR / "m1_extraction_report.csv"

load_dotenv(PROJECT_ROOT / ".env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

ENCODING_FIXES = {
    'â€"':  '-',  'â€˜':  "'",  'â€™':  "'",
    'â€œ':  '"',  'â€\x9d': '"', 'â–¶':  '>',  
    'â€¢':  '-',  'Â ':   ' ',   'â‚¬':  'E',  'â€¦':  '...',
    '\ufffd': '',  '\x00': '',
    chr(226) + chr(134) + chr(146): '->'
}

def normalize_encoding(text: str) -> str:
    for bad, good in ENCODING_FIXES.items():
        text = text.replace(bad, good)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text

def retry_gemini():
    failed_files = [
        "02 Syllabus.pdf",
        "6.23-NB.E.-Mechanical-Engineering-Sem-I-II-2.pdf",
        "6.9N-AIML.pdf",
        "Applied Chemistry syllabus 2024-25.pdf",
        "Professional_Comm._Ethics_Theory_Sem_I 2024-25.pdf",
        "Syllabus-C Prog.pdf"
    ]

    all_new_rows = []
    
    # Read existing report to update it
    report_data = []
    with open(REPORT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            report_data.append(row)
    if REPORT_CSV.exists():
        with open(REPORT_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                report_data.append(row)

    model = genai.GenerativeModel("gemini-1.5-flash")
    models_to_try = [
        "gemini-3.7-flash", 
        "gemini-2.5-flash",
        "gemini-1.5-flash", 
        "gemini-1.5-pro", 
        "gemini-1.5-flash-8b"
    ]

    for pdf_name in failed_files:
        pdf_path = DATA_DIR / pdf_name
        cache_file = REBUILD_DIR / f"gemini_fallback_{pdf_path.stem}.json"
        
        if cache_file.exists():
            print(f"Skipping {pdf_name}, cache exists.")
            continue

        print(f"\nProcessing: {pdf_name}")
        
        doc = fitz.open(str(pdf_path))
        all_text = ""
        for i, page in enumerate(doc):
            if i == 0:
                pt = normalize_encoding(page.get_text("text"))
                if len(pt.strip()) > 100:
                    all_text += pt + "\n"
            else:
                all_text += normalize_encoding(page.get_text("text")) + "\n"
        doc.close()

        all_text = all_text[:30000]

        prompt = f"""You are extracting syllabus data from a Mumbai University PDF.
Extract ALL courses with their topics. Return ONLY valid JSON, no markdown.

Format:
[
  {{
    "course_code": "7-digit code like 3240501 or short code like CSL501",
    "course_name": "Full course name",
    "topics": ["Topic 1", "Topic 2", "Topic 3"]
  }}
]

Rules:
- Include only actual subject topics (not book names, author names, exam info, or administrative text)
- Each topic should be 3-15 words describing a concept or module
- If course code is not available, use the course name initials

Syllabus text:
{all_text}"""
        
        success = False
        for attempt in range(5):
            try:
                print(f"  Attempt {attempt+1}...")
                response = model.generate_content(prompt)
                raw = response.text.strip()
                raw = re.sub(r'^```(?:json)?\s*', '', raw)
                raw = re.sub(r'\s*```$', '', raw)
                data = json.loads(raw)
                
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                courses = [(c.get("course_code", ""), c.get("course_name", ""), c.get("topics", [])) for c in data]
                
                course_count = len(courses)
                topic_count = sum(len(t) for _, _, t in courses)
                print(f"  OK: {course_count} courses, {topic_count} topics")
                
                # Append to flat rows
                for code, name, topics in courses:
                    for topic_idx, topic in enumerate(topics):
                        if not topic or len(topic.strip()) < 4: continue
                        all_new_rows.append({
                            "concept_a": "", "concept_b": "", "source_syllabus": pdf_name,
                            "course_code": code, "course_name": name,
                            "topic_name": topic.strip(), "topic_index": topic_idx,
                            "order_delta": "", "label": "", "reason": "",
                            "domain_match": "", "embedding_similarity": "",
                            "keyword_overlap": "", "extraction_method": "Gemini-fallback"
                        })
                
                # Update report data
                for row in report_data:
                    if row["filename"] == pdf_name:
                        row["status"] = "OK" if topic_count > 0 else "ZERO_TOPICS_FLAGGED"
                        row["courses"] = str(course_count)
                        row["topics"] = str(topic_count)
                        row["method"] = "Gemini-fallback"
                
                success = True
                print("  Sleeping 15s to respect rate limits...")
                time.sleep(15)
        
        for model_name in models_to_try:
            if success:
                break
                
            except Exception as e:
                print(f"  Error: {e}")
                wait_time = 20 * (attempt + 1)
                print(f"  Sleeping {wait_time}s...")
                time.sleep(wait_time)
            print(f"  Trying model: {model_name}")
            model = genai.GenerativeModel(model_name)
            
            for attempt in range(2):
                try:
                    print(f"    Attempt {attempt+1}...")
                    response = model.generate_content(prompt)
                    raw = response.text.strip()
                    raw = re.sub(r'^```(?:json)?\s*', '', raw)
                    raw = re.sub(r'\s*```$', '', raw)
                    data = json.loads(raw)
                    
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    courses = [(c.get("course_code", ""), c.get("course_name", ""), c.get("topics", [])) for c in data]
                    
                    course_count = len(courses)
                    topic_count = sum(len(t) for _, _, t in courses)
                    print(f"    OK: {course_count} courses, {topic_count} topics")
                    
                    # Append to flat rows
                    for code, name, topics in courses:
                        for topic_idx, topic in enumerate(topics):
                            if not topic or len(topic.strip()) < 4: continue
                            all_new_rows.append({
                                "concept_a": "", "concept_b": "", "source_syllabus": pdf_name,
                                "course_code": code, "course_name": name,
                                "topic_name": topic.strip(), "topic_index": topic_idx,
                                "order_delta": "", "label": "", "reason": "",
                                "domain_match": "", "embedding_similarity": "",
                                "keyword_overlap": "", "extraction_method": "Gemini-fallback"
                            })
                    
                    # Update report data
                    for row in report_data:
                        if row["filename"] == pdf_name:
                            row["status"] = "OK" if topic_count > 0 else "ZERO_TOPICS_FLAGGED"
                            row["courses"] = str(course_count)
                            row["topics"] = str(topic_count)
                            row["method"] = "Gemini-fallback"
                    
                    success = True
                    # Just sleep a little between successful API calls
                    time.sleep(2)
                    break
                    
                except Exception as e:
                    print(f"    Error with {model_name}: {e}")
                    time.sleep(2)
                
        if not success:
            print(f"  Failed to process {pdf_name} after 5 attempts.")
            print(f"  Failed to process {pdf_name} with all models.")

    if all_new_rows:
        with open(NEW_ROWS_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "source_syllabus", "course_code", "course_name",
                "topic_name", "topic_index", "extraction_method",
                "concept_a", "concept_b", "order_delta", "label",
                "reason", "domain_match", "embedding_similarity", "keyword_overlap"
            ], extrasaction="ignore")
            writer.writerows(all_new_rows)
        print(f"Appended {len(all_new_rows)} rows to {NEW_ROWS_CSV.name}")
        
    with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=report_data[0].keys())
        writer.writeheader()
        writer.writerows(report_data)
    print("Updated report CSV.")
    if report_data:
        with open(REPORT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=report_data[0].keys())
            writer.writeheader()
            writer.writerows(report_data)
        print("Updated report CSV.")

if __name__ == "__main__":
    retry_gemini()

