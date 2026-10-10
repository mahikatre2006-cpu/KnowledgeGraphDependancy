"""
debug_topics.py
===============
Print raw extracted topic list for two PDFs.
No candidate pairing. No CSV writes.
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.full_pipeline import extract_course_blocks_from_pdf

PDFS = [
    PROJECT_ROOT / "DATA" / "6.34-N-B.E.-Information-Technology-Sem-III-IV.pdf",
    PROJECT_ROOT / "DATA" / "6.40-N-Chemical-Engineering-Sem-III-IV.pdf",
]

OUT_FILE = PROJECT_ROOT / "scripts" / "debug_topics_after.txt"
OUT_FILE = PROJECT_ROOT / "scripts" / "debug_topics_after_v2.txt"

with open(OUT_FILE, "w", encoding="utf-8") as fout:
    for pdf_path in PDFS:
        header = f"\n{'='*70}\nPDF: {pdf_path.name}\n{'='*70}"
        fout.write(header + "\n")
        courses = extract_course_blocks_from_pdf(pdf_path)
        for code, name, topics in courses:
            fout.write(f"\n  [{code}] {name}\n  {'-'*50}\n")
            for i, t in enumerate(topics, 1):
                fout.write(f"    {i:>3}. {t}\n")
        fout.write(f"\n  Total subjects: {len(courses)}\n")
        fout.write(f"  Total topics  : {sum(len(t) for _, _, t in courses)}\n")

print(f"Output written to: {OUT_FILE}")
print("(Open scripts/debug_topics_output.txt to see full raw topic list)")
