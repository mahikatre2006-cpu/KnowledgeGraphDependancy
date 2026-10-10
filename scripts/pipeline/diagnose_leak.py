import re
import sys
import pandas as pd
import pymupdf
from pathlib import Path

project_root = Path(r"c:\Users\Siddhesh\Documents\KnowledgeGraphDependancy")
sys.path.insert(0, str(project_root))

pdf_dir = project_root / "DATA" / "raw" / "2019-scheme" / "Computer-Engineering"
pdfs = [
    ("sem-3", "be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf"),
    ("sem-4", "be_computer-engineering_second-year-se-semester-4-rev-2019-c-scheme.pdf"),
    ("sem-5", "be_computer-engineering_third-year-te-semester-5-rev-2019-c-scheme.pdf"),
    ("sem-6", "be_computer-engineering_third-year-te-semester-6-rev-2019-c-scheme.pdf"),
    ("sem-7-8", "be_computer-engineering_final-year-be-semester-7-8-rev-2019-c-scheme.pdf"),
]

items_to_find = ["Ian Goodfellow", "Oracle Press", "ISBN 978-81-265-5427-0", "Prentice Hall Walter A. Triebel", "Peter Harrington", "Mist Wallet", "Basic Concepts", "Cortana Forensics", "Types of RAM and ROM", "Wiley publication"]

found_count = 0
for _, pdf_name in pdfs:
    doc = pymupdf.open(str(pdf_dir / pdf_name))
    for i, page in enumerate(doc):
        text = page.get_text("text")
        for item in items_to_find[:]:
            if item in text and found_count < 10:
                lines = text.split('\n')
                idx = -1
                for j, line in enumerate(lines):
                    if item in line:
                        idx = j
                        break
                if idx != -1:
                    print(f"Item: '{item}'")
                    print(f"File: {pdf_name}, Page: {i}")
                    start = max(0, idx - 2)
                    end = min(len(lines), idx + 3)
                    print("Context:")
                    for j in range(start, end):
                        print(f"  {lines[j].strip()}")
                    
                    # find previous heading
                    heading = ""
                    for j in range(idx, -1, -1):
                        if re.match(r'^(Text Books?|Reference Books?|References|Assessment|Term Work)', lines[j], re.I) or re.match(r'^(\d+\.\d+|[ivx]+\.)', lines[j]):
                            heading = lines[j].strip()
                            break
                    print(f"Preceding Heading: {heading}\n")
                    items_to_find.remove(item)
                    found_count += 1

