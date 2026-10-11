import sys, random; sys.path.insert(0, ".")
# adjust import/name to what findstr shows
from app.parser.format_router import parse_syllabus_pdf_bytes_routed  # <- placeholder
for pdf in ["DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf",
            "DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf",
            "DATA/raw/2019-scheme/AI-ML/6.21-N-B.E.-AI-ML-sem-III-IV.pdf"]:
    ok, courses, *_ = parse_syllabus_pdf_bytes_routed(open(pdf, "rb").read())
    allt = [t for c in courses for t, _ in c.topics]
    print(pdf.split("/")[-1], len(courses), len(allt))
    for t in random.sample(allt, min(15, len(allt))): print("  ", t)