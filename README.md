# 🧠 Knowledge Dependency Graph (KDG)

An intelligent, implementation-first learning platform that parses unstructured university syllabus PDFs, extracts concepts, builds Directed Acyclic Graphs (DAGs) of prerequisite dependencies, isolates learning bottlenecks, and generates personalized study sequences.

---

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Backend Server
```bash
uvicorn app.main:app --reload
```

### 3. Endpoints & Documentation
* API Root: `http://127.0.0.1:8000/`
* Health Check: `http://127.0.0.1:8000/healthz`
* Swagger OpenAPI Docs: `http://127.0.0.1:8000/docs`

---

## 📂 Project Architecture

```
aiml-knowledge-graph/
├── app/
│   ├── main.py          # FastAPI application entry point
│   ├── core/            # App configuration and settings
│   ├── parser/          # PDF & syllabus text extraction (Phase 4)
│   ├── graph/           # Adjacency list graph engine (Phase 2)
│   ├── services/        # Analytics, topological sorting, & RAG (Phases 3, 6, 7, 8)
│   ├── api/             # REST endpoints and controllers
│   └── models/          # Pydantic schemas & domain models
├── requirements.txt     # Python dependencies
├── .gitignore           # Git ignore rules
└── README.md            # Project documentation
```
