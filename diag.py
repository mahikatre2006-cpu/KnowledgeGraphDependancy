import fitz
p = "tests/fixtures/nep_sem5_6.pdf"
d = fitz.open(p)
t = "\n".join(x.get_text() for x in d)
print("pages", len(d), "chars", len(t))
for m in ["detailed syllabus", "course objectives", "name of module", "self-learning topics", "course code"]:
    print(m, t.lower().count(m))
print(t[:300])