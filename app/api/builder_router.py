import uuid
from typing import Dict, List, Any
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, status
from app.api.graph_router import global_graph
from app.parser.pdf_parser import extract_text_from_pdf_bytes
from app.parser.syllabus_extractor import SyllabusExtractor
from app.services.graph_builder import GraphBuilder
from app.services.sequence_engine import SequenceEngine
from app.models.parser_schemas import ParsedSyllabus
from app.models.graph_schemas import GraphSummaryResponse
from app.models.builder_schemas import BuildGraphResponse, FullPipelineResponse

parsed_sessions: Dict[str, List[ParsedSyllabus]] = {}


class SubjectSummary(BaseModel):
    course_code: str
    course_title: str
    topic_count: int

class ParseResponse(BaseModel):
    document_id: str
    subjects: List[SubjectSummary]

class BuildInferRequest(BaseModel):
    document_id: str
    course_code: str
    clear_existing: bool = True
    add_unit_sequential_edges: bool = True


router = APIRouter(prefix="/pipeline", tags=["End-to-End Syllabus -> Graph Pipeline"])


@router.post("/upload-and-build-graph", response_model=FullPipelineResponse, status_code=status.HTTP_200_OK)
async def upload_and_build_full_pipeline(
    file: UploadFile = File(...),
    clear_existing: bool = Query(default=True, description="Clear existing graph nodes before populating"),
    add_unit_sequential_edges: bool = Query(default=True, description="Add baseline sequence edges between adjacent unit topics")
):
    """
    Seamless End-to-End Pipeline:
    Upload a syllabus PDF file -> Extract raw text -> Parse units & topics -> Instantiate concept graph nodes & edges -> Calculate topological learning sequence.
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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"PDF Processing Error: {str(e)}")

    # 1. Parse syllabus
    parsed_syllabus = SyllabusExtractor.parse(extracted_text)

    # 2. Populate Knowledge Graph
    GraphBuilder.build_from_syllabus(
        syllabus=parsed_syllabus,
        graph=global_graph,
        clear_existing=clear_existing,
        add_unit_sequential_edges=add_unit_sequential_edges
    )

    # 3. Compute Topological Sequence
    sequence = SequenceEngine.get_topological_sequence(global_graph)

    graph_summary = GraphSummaryResponse(
        node_count=global_graph.node_count(),
        edge_count=global_graph.edge_count(),
        nodes=global_graph.get_all_nodes(),
        edges=global_graph.get_all_edges()
    )

    return FullPipelineResponse(
        message=f"Successfully built Knowledge Graph with {global_graph.node_count()} nodes from '{parsed_syllabus.course_title}'",
        parsed_syllabus=parsed_syllabus,
        graph_summary=graph_summary,
        topological_sequence=sequence
    )


@router.post("/build-graph-from-syllabus", response_model=BuildGraphResponse, status_code=status.HTTP_200_OK)
def build_graph_from_syllabus_json(
    syllabus: ParsedSyllabus,
    clear_existing: bool = Query(default=True),
    add_unit_sequential_edges: bool = Query(default=True)
):
    """
    Populates the Knowledge Graph from a pre-parsed syllabus JSON payload.
    """
    stats = GraphBuilder.build_from_syllabus(
        syllabus=syllabus,
        graph=global_graph,
        clear_existing=clear_existing,
        add_unit_sequential_edges=add_unit_sequential_edges
    )

    return BuildGraphResponse(
        message=f"Graph populated with {stats['nodes_added']} nodes.",
        course_title=stats["course_title"],
        course_code=stats["course_code"],
        nodes_added=stats["nodes_added"],
        units_processed=stats["units_processed"]
    )


@router.post("/upload-and-parse", response_model=ParseResponse, status_code=status.HTTP_200_OK)
async def upload_and_parse(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    extracted_text = extract_text_from_pdf_bytes(content)
    
    subjects = SyllabusExtractor.parse_multi(extracted_text)
    
    if not subjects:
        raise HTTPException(status_code=422, detail="No valid subjects or topics could be extracted.")
        
    doc_id = str(uuid.uuid4())
    parsed_sessions[doc_id] = subjects
    
    summaries = []
    for s in subjects:
        summaries.append(SubjectSummary(
            course_code=s.course_code,
            course_title=s.course_title,
            topic_count=s.total_topics_count
        ))
        
    return ParseResponse(document_id=doc_id, subjects=summaries)

@router.post("/build-and-infer", response_model=FullPipelineResponse, status_code=status.HTTP_200_OK)
def build_and_infer(req: BuildInferRequest):
    if req.document_id not in parsed_sessions:
        raise HTTPException(status_code=404, detail="Document ID not found or expired.")
        
    subjects = parsed_sessions[req.document_id]
    
    selected_subject = None
    for s in subjects:
        if s.course_code == req.course_code or len(subjects) == 1:
            selected_subject = s
            break
            
    if not selected_subject:
        raise HTTPException(status_code=404, detail=f"Course code {req.course_code} not found in document.")
        
    # Build Graph
    GraphBuilder.build_from_syllabus(
        syllabus=selected_subject,
        graph=global_graph,
        clear_existing=req.clear_existing,
        add_unit_sequential_edges=req.add_unit_sequential_edges
    )

    # Compute Topological Sequence
    sequence = SequenceEngine.get_topological_sequence(global_graph)

    graph_summary = GraphSummaryResponse(
        node_count=global_graph.node_count(),
        edge_count=global_graph.edge_count(),
        nodes=global_graph.get_all_nodes(),
        edges=global_graph.get_all_edges()
    )

    return FullPipelineResponse(
        message=f"Successfully built Knowledge Graph with {global_graph.node_count()} nodes from '{selected_subject.course_title}'",
        parsed_syllabus=selected_subject,
        graph_summary=graph_summary,
        topological_sequence=sequence
    )
