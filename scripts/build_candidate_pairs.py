import os
import argparse
import csv
import re
from pathlib import Path
import sys

# Ensure the root directory is in sys.path so 'app' can be imported
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.parser.pdf_parser import extract_text_from_pdf_bytes
from app.parser.syllabus_extractor import SyllabusExtractor

def main():
    parser = argparse.ArgumentParser(description="Build candidate concept pairs from syllabus PDFs.")
    parser.add_argument("pdf_folder", type=str, help="Folder path containing raw syllabus PDFs")
    args = parser.parse_args()

    pdf_folder = Path(args.pdf_folder)
    if not pdf_folder.exists() or not pdf_folder.is_dir():
        print(f"Error: Directory '{pdf_folder}' does not exist.")
        sys.exit(1)

    # Output file will be written to data/candidate_pairs.csv in the project root
    data_dir = Path(project_root) / "data"
    data_dir.mkdir(exist_ok=True, parents=True)
    out_csv_path = data_dir / "candidate_pairs.csv"

    candidate_pairs = []

    # 1. Boundary Detection regex: 7-digit numerical Course Code
    course_code_pattern = re.compile(r'\b(\d{7})\b')

    for pdf_path in pdf_folder.glob("*.pdf"):
        print(f"Processing: {pdf_path.name}")
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            raw_text = extract_text_from_pdf_bytes(pdf_bytes)
        except Exception as e:
            print(f"Failed to read {pdf_path.name}: {e}")
            continue

        source_name = pdf_path.name
        
        matches = list(course_code_pattern.finditer(raw_text))
        
        chunks = []
        # 2. Noise Filtration & 3. In-Memory Chunking
        # Everything before the first match is ignored because we start looping from the first match.
        if not matches:
            chunks.append(("UNKNOWN", raw_text))
        else:
            for idx, match in enumerate(matches):
                course_code = match.group(1)
                start_pos = match.start()
                end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw_text)
                chunk_text = raw_text[start_pos:end_pos]
                chunks.append((course_code, chunk_text))

        # 4. Loop Execution
        for course_code, chunk_text in chunks:
            parsed_syllabus = SyllabusExtractor.parse(chunk_text)
            topics = parsed_syllabus.all_topics
            
            # Core order_delta and domain_match logic wrapped in chunk loop
            for i in range(len(topics)):
                for j in range(i + 1, min(i + 15, len(topics))):
                    concept_a = topics[i].name
                    concept_b = topics[j].name
                    order_delta = j - i
                    domain_match = 1 # Assuming same course chunk implies domain match
                    candidate_pairs.append({
                        "concept_a": concept_a,
                        "concept_b": concept_b,
                        "source_syllabus": source_name,
                        "Course_Code": course_code,
                        "order_delta": order_delta,
                        "domain_match": domain_match,
                        "label": ""
                    })

    # 5. Output Update
    with open(out_csv_path, mode="w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["concept_a", "concept_b", "source_syllabus", "Course_Code", "order_delta", "domain_match", "label"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in candidate_pairs:
            writer.writerow(row)

    print(f"\nSuccessfully wrote {len(candidate_pairs)} candidate pairs to {out_csv_path}")

if __name__ == "__main__":
    main()
