import fitz

doc = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf")

# Inspect lines in detailed syllabus section:
lines = []
for p in [19, 20, 21]:
    txt = doc[p-1].get_text("text")
    lines.extend([l.strip() for l in txt.split("\n") if l.strip()])

# Find where DETAILED SYLLABUS starts
start_idx = 0
for idx, l in enumerate(lines):
    if "DETAILED SYLLABUS" in l:
        start_idx = idx
        break

syllabus_lines = lines[start_idx:]
print(f"Total lines after DETAILED SYLLABUS: {len(syllabus_lines)}")
for idx, l in enumerate(syllabus_lines[:80]):
    print(f"{idx}: {l}")

