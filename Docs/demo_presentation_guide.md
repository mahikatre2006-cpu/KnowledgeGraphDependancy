# Knowledge Dependency Graph (KDG) — Demo Presentation Guide

This guide details exactly how to present the engineering, problem-solving, and architecture of the KDG project to your professors, focusing heavily on the Machine Learning model development and the parsing state machine.

---

## 1. Introduction: The Problem & Solution

- **The Problem:** University syllabi are linear PDFs. They don't visually explain the prerequisite dependencies between topics.
- **The Solution:** We built a pipeline that ingests raw PDFs, uses a custom Parsing Engine to extract structured topics, and employs a Machine Learning classifier to infer hidden prerequisite links. Finally, graph algorithms compute the optimal topological learning sequence.

---

## 2. Core Engineering Walkthrough (What to show the Professors)

When explaining the system, walk them through these three major engineering phases, highlighting the issues faced and how you solved them:

### Phase 1: Data Parsing & Cleaning Workflow

_Explain how the raw PDF text is transformed into structured data._

- **The Workflow:**
  1. A raw PDF is uploaded and its text is extracted using `PyMuPDF` (`fitz`).
  2. The text is fed into our custom `SyllabusExtractor` engine.
  3. The engine uses **State Machine logic and Regular Expressions (Regex)** to iterate through the text line-by-line, identifying Unit headers, Course codes, and actual topics while discarding noise (page numbers, random metadata).
- **The Issue:** Initially, processing a multi-subject PDF (like `SEM-V.pdf`) resulted in a massive, unreadable "hairball" graph of 185+ nodes because the parser was squashing all subjects together.
- **The Solution & Proof:** We upgraded the parser to handle multiple subjects accurately.
  - **Show File:** `app/parser/syllabus_extractor.py` -> `parse_multi()`
  - **Explain:** Point out `COURSE_CODE_REGEX = re.compile(r'\b(\d{7}|[A-Z]{2,4}\s*[-:]?\s*\d{3,4})\b', re.IGNORECASE)`. Explain how previously, the system discarded these lines as noise. We realized these course codes are perfect **Boundary Markers**. Now, our state machine intercepts any line matching this regex, safely closes the previous subject bucket, and starts a new one. This reduced graph complexity from 185 unreadable nodes down to ~15 highly targeted nodes per subject.

### Phase 2: Machine Learning Model Development

_Explain how the AI brain was built and trained._

- **Model Development:** We engineered features based on syllabus text (TF-IDF, word overlaps, sequential distance) and trained an **XGBoost Classifier** (`XGBClassifier`) using 5-Fold Cross Validation.
- **The Issue (The "Contaminated Data & 0.5 Threshold" Problem):**
  1. Early on, our dataset had noise which resulted in a flawed model (`model_artifact.joblib`).
  2. Furthermore, using the standard ML probability threshold of `0.5` was too strict. The model was predicting too many False Negatives (saying topics weren't related when they were), which resulted in sparse, disconnected graphs.
- **The Solution & Proof:**
  - **Show File:** `app/ml/train_classifier.py` and `app/ml/model_artifact_v3.joblib`. Explain how you cleaned the dataset and retrained the model to `v3` to fix the data contamination.
  - **Show File:** `app/ml/decision_threshold.json` and `frontend/src/App.jsx`.
  - **Explain:** We wrote a custom script (`threshold_analysis.py`) to sweep across probability thresholds. We discovered that a threshold of **`0.20`** drastically improved the F1-score and Recall, ensuring prerequisite links were accurately captured. Show them how the frontend dynamically imports this optimized JSON file (`thresholdConfig.optimal_threshold`) instead of hardcoding `0.5`.

### Phase 3: System Architecture & API Separation

_Explain how the backend handles the flow securely._

- **The Issue:** Uploading, parsing, inferring, and graphing all at once for multi-subject PDFs was computationally heavy and provided bad UX.
- **The Solution & Proof:**
  - **Show File:** `app/api/builder_router.py`
  - **Explain:** We broke the API into a two-step state machine. Step A (`/upload-and-parse`) processes the regex parsing and temporarily saves the subject buckets into a fast in-memory dictionary (`parsed_sessions`). The frontend then renders a Subject Picker UI. Once the user selects a subject, Step B (`/build-and-infer`) processes _only_ that subset through the ML model.

---

## 3. The Live Demo Execution

Execute the demo while referencing the technical points above:

1.  **Upload `SEM-V.pdf`:** Show the UI correctly popping up the **Subject Picker**. Mention Phase 1 (Regex Boundary Detection).
2.  **Select a Subject:** Click a specific subject (e.g., `2165511`). Watch the graph render. Mention Phase 3 (API separation efficiency).
3.  **Analyze the Graph:** Point to the directional arrows. Mention Phase 2 (the tuned `0.20` XGBoost model making these connections).
4.  **Show the Analytics:** Draw attention to the **Topological Sequence** and explain that after the ML infers the graph, traditional DAG (Directed Acyclic Graph) algorithms run to calculate the ultimate learning path.
