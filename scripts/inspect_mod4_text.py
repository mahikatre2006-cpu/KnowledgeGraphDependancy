import fitz
import sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf")
print("=== Page 20 Text ===")
print(doc[19].get_text("text"))

