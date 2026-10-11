"""
builder_router.py — NEP-aware pipeline router (fix/nep-parser)
"""
import uuid
from time import perf_counter
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, status

from app.api.graph_router import global_graph
from app.parser.pdf_parser import extract_text_from_pdf_bytes
from app.parser.syllabus_extractor import SyllabusExtractor
from app.parser.nep_parse_v2 import parse_nep_pdf_bytes, is_syllabus, NEPCourse, NEPModule
from app.services.graph_builder import GraphBuilder
from app.services.sequence_engine import SequenceEngine
from app.services.relationship_inferencer import RelationshipInferencer
from app.models.parser_schemas import ParsedSyllabus, ParsedUnit, ParsedTopic
from app.models.graph_schemas import GraphSummaryResponse
from app.models.builder_schemas import BuildGraphResponse, FullPipelineResponse

# ── In-process session store ──────────────────────────────────────────────────
parsed_sessions: Dict[str, List[NEPCourse]] = {}

MAX_NODES = 120


class SubjectSummary(BaseModel):
    course_code: str
    course_title: str
    topic_count: int
    kind: str = "theory"


class ParseResponse(BaseModel):
    document_id: str
    subjects: List[SubjectSummary]


class BuildInferRequest(BaseModel):
    document_id: str
    course_code: Optional[str] = None   # default: first theory course
    clear_existing: bool = True
    add_unit_sequential_edges: bool = True


router = APIRouter(prefix="/pipeline", tags=["End-to-End Syllabus -> Graph Pipeline"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _nep_course_to_parsed_syllabus(course: NEPCourse) -> ParsedSyllabus:
    """Convert NEPCourse to ParsedSyllabus for downstream compatibility."""
    units: List[ParsedUnit] = []
    all_topics: List[ParsedTopic] = []

    for mod in course.modules:
        topics_for_unit: List[ParsedTopic] = []
        mod_topics = getattr(mod, "topics", None) if not isinstance(mod, dict) else mod.get("topics", [])
        mod_idx = getattr(mod, "index", None) or getattr(mod, "idx", None) if not isinstance(mod, dict) else mod.get("idx", 1)
        mod_title = getattr(mod, "name", None) or getattr(mod, "title", None) if not isinstance(mod, dict) else mod.get("title", "")
        for name in mod_topics:
            slug = _slugify(name)
            pt = ParsedTopic(
                id=slug,
                name=name,
                unit_number=mod_idx,
                unit_title=mod_title,
            )
            topics_for_unit.append(pt)
            all_topics.append(pt)

        if topics_for_unit:
            units.append(ParsedUnit(
                unit_number=mod_idx,
                title=mod_title,
                topics=topics_for_unit,
            ))

    return ParsedSyllabus(
        course_title=course.title,
        course_code=course.code,
        units=units,
        all_topics=all_topics,
        total_topics_count=len(all_topics),
    )


def _slugify(text: str) -> str:
    import re
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    return slug.strip('_')


def _handle_raw_text_fallback(content: bytes) -> Optional[List[NEPCourse]]:
    """
    Fallback for raw-text / legacy format PDFs that do not match the strict NEP gate.
    Bypasses the PDF syllabus gate if SyllabusExtractor extracts valid units and topics.
    Rejects calendar/circular text with None.
    """
    import re
    raw_text = extract_text_from_pdf_bytes(content)
    junk_patterns = [
        r'\b(break|holiday|vacation)\b',
        r'\bunit\s+test\b',
        r'\bcarried\b',
        r'\ball\s+subjects\b',
    ]
    if any(re.search(p, raw_text, re.IGNORECASE) for p in junk_patterns):
        return None
    legacy_parsed = SyllabusExtractor.parse(raw_text)
    if legacy_parsed and legacy_parsed.units and any(u.topics for u in legacy_parsed.units):
        modules = [
            NEPModule(
                index=u.unit_number,
                name=u.title,
                topics=[t.name for t in u.topics],
            )
            for u in legacy_parsed.units
        ]
        course = NEPCourse(
            code=legacy_parsed.course_code or "CS301",
            title=legacy_parsed.course_title or "Syllabus",
            kind="theory",
            modules=modules,
        )
        return [course]
    return None


def _select_course(courses: List[NEPCourse], course_code: Optional[str]) -> Optional[NEPCourse]:
    """Select course by code, or fall back to first theory course."""
    if course_code:
        for c in courses:
            if c.code == course_code:
                return c
        return None
    # Default: first theory course
    for c in courses:
        if c.kind == 'theory':
            return c
    return courses[0] if courses else None


def _layered_positions(nodes):
    """
    Longest-path layered layout: x = layer*280, y = index*90.
    Fallback to sequential if graph has no edges.
    Returns dict: node_id -> {x, y}
    """
    import networkx as nx
    G = nx.DiGraph()
    node_ids = [n.id for n in nodes]
    G.add_nodes_from(node_ids)

    # Build a rough layer by unit/order
    # Without full graph edges here, assign layer = unit number extracted from metadata
    import re
    positions = {}
    unit_buckets: Dict[int, List] = {}
    for n in nodes:
        m = re.search(r'\d+', n.unit or '')
        layer = int(m.group()) if m else 0
        unit_buckets.setdefault(layer, []).append(n)

    for layer, ns in sorted(unit_buckets.items()):
        for idx, n in enumerate(ns):
            positions[n.id] = {"x": layer * 280, "y": idx * 90}

    return positions


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload-and-parse", response_model=ParseResponse, status_code=status.HTTP_200_OK)
async def upload_and_parse(file: UploadFile = File(...)):
    """
    Stage 1: Upload PDF -> gate check -> segment courses.
    Returns document_id + course list for subject selection.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    t_parse_start = perf_counter()
    content = await file.read()

    # NEP parser (includes gate)
    gate_ok, courses, parse_s = parse_nep_pdf_bytes(content)
    t_parse_total = perf_counter() - t_parse_start

    print(f"[TIMING] parse={parse_s:.3f}s  total_upload_parse={t_parse_total:.3f}s")

    if not gate_ok or not courses:
        fallback_courses = _handle_raw_text_fallback(content)
        if fallback_courses:
            courses = fallback_courses
            gate_ok = True
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "not_a_syllabus"}
            )

    doc_id = str(uuid.uuid4())
    parsed_sessions[doc_id] = courses

    summaries = [
        SubjectSummary(
            course_code=c.code,
            course_title=c.title,
            topic_count=len(c.topics),
            kind=c.kind,
        )
        for c in courses
    ]
    return ParseResponse(document_id=doc_id, subjects=summaries)


@router.post("/build-and-infer", response_model=FullPipelineResponse, status_code=status.HTTP_200_OK)
def build_and_infer(req: BuildInferRequest):
    """
    Stage 2: Build graph + run ML inference for selected course.
    Accepts optional course_code; defaults to first theory course.
    """
    if req.document_id not in parsed_sessions:
        raise HTTPException(status_code=404, detail="Document ID not found or expired.")

    courses = parsed_sessions[req.document_id]
    selected = _select_course(courses, req.course_code)

    if not selected:
        raise HTTPException(
            status_code=404,
            detail=f"Course code '{req.course_code}' not found in document."
        )

    # Node cap
    if len(selected.topics) > MAX_NODES:
        raise HTTPException(
            status_code=422,
            detail=f"Course has {len(selected.topics)} nodes; max is {MAX_NODES}."
        )

    parsed_syllabus = _nep_course_to_parsed_syllabus(selected)

    # Build Graph
    t0 = perf_counter()
    GraphBuilder.build_from_syllabus(
        syllabus=parsed_syllabus,
        graph=global_graph,
        clear_existing=req.clear_existing,
        add_unit_sequential_edges=req.add_unit_sequential_edges,
    )
    t_graph = perf_counter() - t0
    print(f"[TIMING] graph_build={t_graph:.3f}s  nodes={global_graph.node_count()}")

    # Infer Prerequisites via trained local ML model
    t0 = perf_counter()
    RelationshipInferencer.infer_prerequisites(
        graph=global_graph,
        auto_add_to_graph=True,
    )
    t_infer = perf_counter() - t0
    print(f"[TIMING] infer={t_infer:.3f}s  edges={global_graph.edge_count()}")

    # Compute Topological Sequence
    sequence = SequenceEngine.get_topological_sequence(global_graph)

    # Layered positions on nodes
    nodes = global_graph.get_all_nodes()
    positions = _layered_positions(nodes)
    for n in nodes:
        if n.id in positions:
            n.metadata["position"] = positions[n.id]

    graph_summary = GraphSummaryResponse(
        node_count=global_graph.node_count(),
        edge_count=global_graph.edge_count(),
        nodes=nodes,
        edges=global_graph.get_all_edges(),
    )

    return FullPipelineResponse(
        message=(
            f"Successfully built Knowledge Graph with {global_graph.node_count()} nodes "
            f"from '{selected.title}'"
        ),
        parsed_syllabus=parsed_syllabus,
        graph_summary=graph_summary,
        topological_sequence=sequence,
    )


# ── Legacy endpoints (kept for backward compat) ────────────────────────────────

@router.post(
    "/upload-and-build-graph",
    response_model=FullPipelineResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_and_build_full_pipeline(
    file: UploadFile = File(...),
    clear_existing: bool = Query(default=True),
    add_unit_sequential_edges: bool = Query(default=True),
    run_inference: bool = Query(default=False),
):
    """Legacy single-shot endpoint (still gate-checked)."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invalid file format. Only PDF (.pdf) files are supported.")

    content = await file.read()

    gate_ok, courses, _ = parse_nep_pdf_bytes(content)
    if not gate_ok or not courses:
        fallback_courses = _handle_raw_text_fallback(content)
        if fallback_courses:
            courses = fallback_courses
            gate_ok = True
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error": "not_a_syllabus"},
            )

    selected = _select_course(courses, None)
    if not selected:
        raise HTTPException(status_code=422, detail="No valid courses found.")

    parsed_syllabus = _nep_course_to_parsed_syllabus(selected)

    GraphBuilder.build_from_syllabus(
        syllabus=parsed_syllabus,
        graph=global_graph,
        clear_existing=clear_existing,
        add_unit_sequential_edges=add_unit_sequential_edges,
    )

    if run_inference:
        RelationshipInferencer.infer_prerequisites(graph=global_graph, auto_add_to_graph=True)

    sequence = SequenceEngine.get_topological_sequence(global_graph)

    graph_summary = GraphSummaryResponse(
        node_count=global_graph.node_count(),
        edge_count=global_graph.edge_count(),
        nodes=global_graph.get_all_nodes(),
        edges=global_graph.get_all_edges(),
    )

    return FullPipelineResponse(
        message=f"Successfully built Knowledge Graph with {global_graph.node_count()} nodes from '{selected.title}'",
        parsed_syllabus=parsed_syllabus,
        graph_summary=graph_summary,
        topological_sequence=sequence,
    )


@router.post(
    "/build-graph-from-syllabus",
    response_model=BuildGraphResponse,
    status_code=status.HTTP_200_OK,
)
def build_graph_from_syllabus_json(
    syllabus: ParsedSyllabus,
    clear_existing: bool = Query(default=True),
    add_unit_sequential_edges: bool = Query(default=True),
):
    """Populates the Knowledge Graph from a pre-parsed syllabus JSON payload."""
    stats = GraphBuilder.build_from_syllabus(
        syllabus=syllabus,
        graph=global_graph,
        clear_existing=clear_existing,
        add_unit_sequential_edges=add_unit_sequential_edges,
    )
    return BuildGraphResponse(
        message=f"Graph populated with {stats['nodes_added']} nodes.",
        course_title=stats["course_title"],
        course_code=stats["course_code"],
        nodes_added=stats["nodes_added"],
        units_processed=stats["units_processed"],
    )
