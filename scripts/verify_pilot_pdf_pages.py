import fitz
import sys

sys.stdout.reconfigure(encoding='utf-8')

pilot_subjects = [
    {
        "course_code": "ITC501",
        "title": "Internet Programming",
        "semester": "V",
        "pdf": "DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf",
        "pages": [12, 13, 14]
    },
    {
        "course_code": "CSC303",
        "title": "Data Structure",
        "semester": "III",
        "pdf": "DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf",
        "pages": [13, 14]
    },
    {
        "course_code": "2113112",
        "title": "Discrete Structures and Graph Theory",
        "semester": "III",
        "pdf": "DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf",
        "pages": [19, 20, 21]
    }
]

for s in pilot_subjects:
    doc = fitz.open(s["pdf"])
    print(f"=== {s['course_code']} ({s['title']}) ===")
    for p in s["pages"]:
        txt = doc[p-1].get_text("text").strip()
        print(f"  Page {p}: length={len(txt)} chars, preview: {repr(txt[:80])}")

