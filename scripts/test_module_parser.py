import fitz
import re

doc = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf")

# Check pages 19, 20, 21
full_text = ""
for p in [19, 20, 21]:
    full_text += f"\n--- Page {p} ---\n" + doc[p-1].get_text("text")

print("Parsing modules in 2113112:")
# In Mumbai University syllabus tables, modules are indexed with Roman numerals I, II, III, IV, V, VI, or numbers 0, 1, 2, 3...
# Lines typically look like:
# Sr. No. | Module Name / Name of Module
lines = full_text.split('\n')
for i, l in enumerate(lines):
    # Roman numerals or Module digits
    m = re.match(r'^(0|I|II|III|IV|V|VI|VII|VIII|[1-6])\s*$', l.strip())
    if m:
        num = m.group(1)
        # Next non-empty lines could be module name
        name_lines = []
        for j in range(i+1, min(i+5, len(lines))):
            jl = lines[j].strip()
            if not jl: continue
            if re.match(r'^(0|I|II|III|IV|V|VI|VII|VIII|[1-6]|\d+\s*Hours|CO\d|Self-learning|DETAILED)', jl):
                break
            name_lines.append(jl)
        mod_name = " ".join(name_lines)
        print(f"Found Module index {num}: {mod_name} (around line {i})")

