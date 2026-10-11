import fitz
import re
from pathlib import Path

def inspect_fe_details():
    fe_files = ["6.22-NIT.pdf", "6.9N-AIML.pdf", "6.14N-CSE-AIML.pdf", "6.28N-DS.pdf"]
    for fname in fe_files:
        p = list(Path("DATA/raw/2019-scheme").rglob(fname))[0]
        doc = fitz.open(p)
        print(f"=== {fname} (Total pages: {len(doc)}) ===")
        # search for Program Structure
        for page_num in range(len(doc)):
            txt = doc[page_num].get_text("text")
            if "Program Structure" in txt or "Semester I" in txt or "Semester II" in txt:
                lines = [l.strip() for l in txt.split('\n') if l.strip()]
                # find if there are tables with course codes
                codes = [l for l in lines if re.match(r'^(BSC|ESC|BSL|ESL|AEC|AEL|VSEC|CC|IKS|PCC|PCL)\d{3}', l)]
                if codes:
                    print(f"  Page {page_num+1}: found {len(codes)} codes: {codes[:8]}...")

inspect_fe_details()

