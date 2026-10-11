import fitz
d = fitz.open("tests/fixtures/REAL_nep.pdf")
lines = []
for p in d:
    lines += [l.strip() for l in p.get_text().splitlines() if l.strip()]
i = next(k for k, l in enumerate(lines) if l.lower().startswith("detailed syllabus"))
j = next(k for k, l in enumerate(lines) if l == "2345111" or l.startswith("2345111"))
print("FIRST HEADER AT", j, "FIRST DETAILED SYLLABUS AT", i)
print("\n".join(lines[j:j+30]))
print("-----")
print("\n".join(lines[i-3:i+45]))