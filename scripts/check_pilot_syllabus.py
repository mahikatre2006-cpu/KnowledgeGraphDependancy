import sys
sys.stdout.reconfigure(encoding='utf-8')
import fitz

doc_comps = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf")
print("=== CSC303 Page 13 ===")
print(doc_comps[12].get_text("text"))
print("=== CSC303 Page 14 ===")
print(doc_comps[13].get_text("text"))

doc_nep = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf")
print("=== 2113112 Page 19 ===")
print(doc_nep[18].get_text("text"))
print("=== 2113112 Page 20 ===")
print(doc_nep[19].get_text("text"))
print("=== 2113112 Page 21 ===")
print(doc_nep[20].get_text("text"))

