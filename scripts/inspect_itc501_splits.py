import fitz
import sys
sys.stdout.reconfigure(encoding='utf-8')

doc = fitz.open("DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf")
print("=== ITC501 Page 13 Text ===")
print(doc[12].get_text("text"))

