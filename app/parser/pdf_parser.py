import re
import fitz  # PyMuPDF


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Extracts raw text from PDF bytes using PyMuPDF (fitz).
    Cleans up control characters, repeated spaces, and page artifacts.

    Raises:
        ValueError: If PDF bytes are invalid or unreadable.
    """
    if not pdf_bytes:
        raise ValueError("Empty PDF file provided.")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Failed to open PDF document: {str(e)}")

    if doc.page_count == 0:
        raise ValueError("PDF document contains no pages.")

    full_text_pages = []

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        if text and text.strip():
            full_text_pages.append(text.strip())

    doc.close()

    raw_text = "\n\n".join(full_text_pages)
    return clean_pdf_text(raw_text)


def clean_pdf_text(text: str) -> str:
    """
    Normalizes extracted PDF text by fixing line wraps, stripping noise,
    and standardizing whitespace.
    """
    # Remove control characters except newline & tab
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # Normalize multiple horizontal spaces into single space
    text = re.sub(r'[ \t]+', ' ', text)

    # Fix hyphenated word breaks at end of lines (e.g., "Linear Al- \n gebra" -> "Linear Algebra")
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)

    # Replace 3 or more consecutive newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()
