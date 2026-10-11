import fitz

def print_page_text(pdf_path, pages, label):
    doc = fitz.open(pdf_path)
    print(f"\n==================== {label} ====================")
    for p in pages:
        print(f"\n--- Page {p} ---")
        lines = doc[p-1].get_text("text").split('\n')
        for l in lines[:25]:
            print(f"  {l}")
        if len(lines) > 25:
            print(f"  ... [{len(lines)-25} more lines]")

print_page_text("DATA/raw/2019-scheme/Information-Technology/6.12-T.E.-Information_Technology-Sem.-V-VI1.pdf", [12, 13, 14], "ITC501 (Internet Programming)")
print_page_text("DATA/raw/2019-scheme/Computer-Engineering/be_computer-engineering_second-year-se-semester-3-rev-2019-c-scheme.pdf", [13, 14], "CSC303 (Data Structure)")
print_page_text("DATA/raw/2019-scheme/Computer-Engineering/6.24-N-B.E.-Computer-Engineering-Sem-III-IV.pdf", [19, 20, 21], "2113112 (Discrete Structures & Graph Theory)")

