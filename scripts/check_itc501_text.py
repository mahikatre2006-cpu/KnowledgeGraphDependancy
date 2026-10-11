import fitz

doc_it = fitz.open("DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf")
print("ITC501 page 13 text:")
print(doc_it[12].get_text("text"))

print("ITC501 page 14 text:")
print(doc_it[13].get_text("text")[:1000])

