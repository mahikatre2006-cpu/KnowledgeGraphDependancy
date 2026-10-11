import fitz

doc = fitz.open("DATA/raw/2019-scheme/Information-Technology/6.22-NIT.pdf")
print("=== 6.22-NIT Page 9 (Sem I Teaching Scheme) ===")
print(doc[8].get_text("text"))
print("=== 6.22-NIT Page 11 (Sem II Teaching Scheme) ===")
print(doc[10].get_text("text"))

