import fitz
import re

def inspect_subject(pdf_path, pages, name):
    doc = fitz.open(pdf_path)
    full_text = "\n".join([f"--- Page {p} ---\n" + doc[p-1].get_text("text") for p in pages])
    print(f"\n==================== {name} ====================")
    lines = full_text.split('\n')
    for i, l in enumerate(lines):
        if any(k in l.lower() for k in ["prerequisite", "self-learning", "module", "detailed syllabus"]):
            print(f"L{i}: {l}")

inspect_subject("DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf", [12, 13, 14], "ITC501")
inspect_subject("DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf", [13, 14], "CSC303")
inspect_subject("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf", [19, 20, 21], "2113112")

