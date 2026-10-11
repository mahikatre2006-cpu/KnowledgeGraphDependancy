"""
Script to generate tests/fixtures/nep_sem5_6.pdf
NEP 2026-27 IT Sem V & VI fixture PDF.

Run once: venv\Scripts\python.exe tests\create_fixture_pdf.py
"""
import os
import fitz  # PyMuPDF

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
os.makedirs(FIXTURE_DIR, exist_ok=True)
OUT_PATH = os.path.join(FIXTURE_DIR, "nep_sem5_6.pdf")


def add_course_page(doc, code, name, kind, modules):
    """Add one course to the PDF document."""
    page = doc.new_page(width=595, height=842)  # A4
    y = 40

    def write(text, x=40, step=14, size=9):
        nonlocal y
        page.insert_text((x, y), text, fontsize=size)
        y += step

    # Course header
    write(f"Course Code | Course Name | Teaching Scheme", size=10)
    write(f"{code}  {name}", size=10)
    write("Theory  Practical  Tutorial  Credits", size=8)
    write("3  0  0  3", size=8)
    y += 5

    if kind == 'lab':
        write("Lab Objectives:", size=9)
        write("1. Students will implement programs.", size=8)
        write("2. Students will write test cases.", size=8)
    else:
        write("Course Objectives:", size=9)
        write("1. Understand core concepts.", size=8)
        write("2. Apply knowledge practically.", size=8)

    write("Course Outcomes:", size=9)
    write("CO1: Demonstrate knowledge of fundamentals.", size=8)
    write("CO2: Analyze and design solutions.", size=8)
    y += 5

    write("Detailed Syllabus:", size=10)
    write("Sr. No.  Name of Module  Detailed Content  Hours  CO Mapping", size=8)
    write("0  Prerequisite  Data Structures, Mathematics, Programming  00", size=8)
    y += 5

    for mod_num, mod_title, content_items in modules:
        content_str = ", ".join(content_items)
        write(f"{mod_num}  {mod_title}", size=9)
        # Write content in chunks to simulate table rows
        # Add Self-Learning at end of some modules (to be excluded)
        write(f"   {content_str}", size=8)
        write(f"   Self-Learning Topics: Explore online resources for deeper understanding.  06 CO1", size=7)

    y += 5
    write("Total Hours: 48", size=9)
    y += 3
    write("Note: No questions from Self-Learning topics.", size=8)
    write("Text Books:", size=8)
    write("1. Web Development by J. Smith, Pearson, 2nd edition.", size=8)
    write("References:", size=8)
    write("1. MDN Web Docs. https://developer.mozilla.org", size=8)
    write("Assessment:", size=8)
    write("IAT-I + IAT-II: 40 Marks, End Sem: 60 Marks", size=8)


# ── Course 1: 2345113 Web Technology ──────────────────────────────────────────
WT_MODULES = [
    (1, "Web Fundamentals and JavaScript", [
        "HTML5 semantic elements", "CSS3 box model", "DOM manipulation",
        "event handling", "arrow functions", "closures",
        "promises and async/await", "event loops", "AJAX and fetch API",
    ]),
    (2, "React.js Frontend Development", [
        "component lifecycle", "state and props", "hooks",
        "virtual DOM", "React Router", "conditional rendering",
        "forms and validation", "context API",
    ]),
    (3, "Node.js and Express Backend", [
        "Node.js runtime", "REPL", "CommonJS modules",
        "express router", "middleware stack", "REST API",
        "error handling", "JWT authentication",
    ]),
    (4, "Database Integration", [
        "MongoDB schema design", "CRUD operations", "aggregation pipeline",
        "Mongoose ORM", "SQL vs NoSQL", "indexing strategies",
        "transactions",
    ]),
    (5, "MVC and Design Patterns", [
        "model-view-controller", "model-view", "separation of concerns",
        "repository pattern", "service layer", "dependency injection",
    ]),
    (6, "Security and Deployment", [
        "CSP headers", "XSS prevention", "CORS policy",
        "HTTPS and TLS", "OAuth2 flow", "Docker containerization",
        "CI/CD pipeline basics",
    ]),
]

# ── Course 2: 2345111 Software Engineering and Agile Practices ─────────────
SE_MODULES = [
    (1, "SDLC and Process Models", [
        "waterfall model", "incremental model", "spiral model",
        "RAD model", "COCOMO estimation", "function point analysis",
        "project planning",
    ]),
    (2, "Requirements Engineering", [
        "use case diagrams", "user stories", "requirements elicitation",
        "functional and non-functional requirements", "prototyping",
        "RMMM risk matrix",
    ]),
    (3, "Agile Methodologies", [
        "scrum framework", "sprint planning", "daily standup",
        "kanban board", "retrospective", "velocity tracking",
        "burndown chart",
    ]),
    (4, "Software Design", [
        "UML diagrams", "class diagrams", "sequence diagrams",
        "design patterns", "SOLID principles", "cohesion and coupling",
    ]),
    (5, "Software Testing", [
        "unit testing", "integration testing", "system testing",
        "regression testing", "black-box testing", "white-box testing",
        "equivalence partitioning", "test-driven development",
    ]),
    (6, "Maintenance and Quality", [
        "software maintenance types", "refactoring", "code review",
        "SQA metrics", "ISO standards", "configuration management",
    ]),
]

# ── Course 3: 2345112 AI and ML ───────────────────────────────────────────────
ML_MODULES = [
    (1, "AI Foundations and Search", [
        "problem formulation", "state space search", "breadth first search",
        "depth first search", "A* algorithm", "heuristic functions",
        "adversarial search",
    ]),
    (2, "Knowledge Representation", [
        "propositional logic", "first-order logic", "Bayesian networks",
        "inference rules", "resolution refutation",
    ]),
    (3, "Supervised Learning", [
        "linear regression", "logistic regression", "decision trees",
        "random forest", "support vector machine", "naive Bayes classifier",
        "gradient descent",
    ]),
    (4, "Unsupervised Learning", [
        "k-means clustering", "hierarchical clustering",
        "principal component analysis", "dimensionality reduction",
        "association rule mining", "apriori algorithm",
    ]),
    (5, "Model Evaluation", [
        "confusion matrix", "precision and recall", "F1 score",
        "ROC curve", "AUC score", "cross-validation", "bias-variance tradeoff",
    ]),
    (6, "Neural Networks", [
        "perceptron model", "multilayer perceptron", "backpropagation",
        "activation functions", "convolutional neural networks",
        "recurrent neural networks", "transfer learning",
    ]),
]

# ── Lab course ────────────────────────────────────────────────────────────────
LAB_MODULES = [
    (1, "Web Development Lab", [
        "implement REST endpoints", "build React components",
        "connect MongoDB", "deploy on cloud",
    ]),
]


doc = fitz.open()

add_course_page(doc, "2345111", "Software Engineering and Agile Practices", "theory", SE_MODULES)
add_course_page(doc, "2345112", "AI and ML", "theory", ML_MODULES)
add_course_page(doc, "2345113", "Web Technology", "theory", WT_MODULES)
add_course_page(doc, "2345114L", "Web Technology Lab", "lab", LAB_MODULES)

doc.save(OUT_PATH)
doc.close()
print(f"Created fixture: {OUT_PATH}")

