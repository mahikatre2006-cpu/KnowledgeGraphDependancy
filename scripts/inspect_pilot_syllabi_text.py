import fitz
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("INSPECTING SYLLABUS PAGES IN LOCAL PDFS")
print("=" * 80)

# ITC501
doc_itc = fitz.open("DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf")
print("\n--- ITC501 (Pages 12-14) ---")
for p in [12, 13, 14]:
    print(f"--- PAGE {p} ---")
    print(doc_itc[p-1].get_text("text"))

# CSC303
doc_csc = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf")
print("\n--- CSC303 (Pages 13-14) ---")
for p in [13, 14]:
    print(f"--- PAGE {p} ---")
    print(doc_csc[p-1].get_text("text"))

# 2113112
doc_211 = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf")
print("\n--- 2113112 (Pages 19-21) ---")
for p in [19, 20, 21]:
    print(f"--- PAGE {p} ---")
    print(doc_211[p-1].get_text("text"))

