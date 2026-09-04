from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.parser.pdf_parser import extract_text_from_pdf_bytes
from app.parser.syllabus_extractor import SyllabusExtractor
from app.models.parser_schemas import ParsedSyllabus, ParseTextRequest

router = APIRouter(prefix="/syllabus", tags=["Syllabus PDF Parser Engine"])


@router.post("/upload", response_model=ParsedSyllabus, status_code=status.HTTP_200_OK)
async def upload_and_parse_syllabus(file: UploadFile = File(...)):
    """
    Uploads a university syllabus PDF file, extracts raw text, detects units & modules,
    and returns a structured JSON hierarchy of extracted topics.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF (.pdf) files are supported."
        )

    try:
        content = await file.read()
        extracted_text = extract_text_from_pdf_bytes(content)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process PDF file: {str(e)}"
        )

    parsed_syllabus = SyllabusExtractor.parse(extracted_text)
    return parsed_syllabus


@router.post("/parse-text", response_model=ParsedSyllabus, status_code=status.HTTP_200_OK)
def parse_syllabus_text(request: ParseTextRequest):
    """
    Parses raw text of a syllabus directly into structured Units & Topics JSON without PDF upload.
    """
    return SyllabusExtractor.parse(request.text)
