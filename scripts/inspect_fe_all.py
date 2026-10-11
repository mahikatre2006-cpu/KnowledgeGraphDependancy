import fitz

for fname in ["6.22-NIT.pdf", "6.9N-AIML.pdf", "6.14N-CSE-AIML.pdf", "6.28N-DS.pdf"]:
    doc = fitz.open(f"DATA/raw/2019-scheme/{'Information-Technology' if 'NIT' in fname else 'Computer-Engineering'}/{fname}")
    print(f"=== {fname} Pages 9-13 ===")
    for p in range(8, 14):
        txt = doc[p].get_text("text")
        print(f"--- Page {p+1} ---")
        for line in txt.split("\n"):
            line = line.strip()
            if any(k in line for k in ["VSEC", "PCC", "BSC", "ESC", "CC", "IKS", "AEC"]):
                print("  ", line)

