import sys; sys.path.insert(0, ".")
from app.parser.nep_parse_v2 import parse_nep_pdf_bytes
ok, cs, t = parse_nep_pdf_bytes(open("tests/fixtures/REAL_nep.pdf", "rb").read())
print(ok, len(cs), round(t, 1))
for c in cs:
    print(c.code, c.kind, c.title, c.n_topics, [len(m.topics) for m in c.modules])
c = next(c for c in cs if c.code == "2345113")
for m in c.modules: print(m.index, m.name, m.topics)
low = " ".join(t.lower() for t, _ in c.topics)
for s in ["arrow functions","hooks","crud operations","event loops","express router","rest api","model-view"]:
    print("MUST", s, s in low)
for s in ["asynchronous javascript","react native","fastapi","next.js framework","react vs angular","query optimization","environment setup","first app","internet basics"]:
    print("BAD ", s, s in low)