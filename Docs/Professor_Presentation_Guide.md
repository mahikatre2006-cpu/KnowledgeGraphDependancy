# Knowledge Graph Dependency — Professor Presentation Guide

This document is designed to help you explain the core machine learning and data pipeline to an academic or technical audience, specifically professors. It focuses on the methodology, the flow of data, and defends the mathematical and architectural choices made during development.

---

## 1. The Core Problem

University syllabi are unstructured text documents (PDFs). While they present topics in a linear order, they do not explicitly define **prerequisite relationships** (e.g., you must learn _Matrix Algebra_ before _Deep Learning_). This project automates the extraction of these hidden dependencies to build a directed Knowledge Graph.

---

## 2. The End-to-End ML Workflow

The pipeline operates in five distinct phases:

### Phase 1: Data Extraction (PDF to Text)

We parse raw university syllabus PDFs. Using advanced Regular Expressions, we locate course codes (e.g., `CSC301`) and extract the chronological list of topics taught in that course, preserving the exact order defined by the university.

### Phase 2: Candidate Pair Generation

Because prerequisites flow forward in time, we generate candidate pairs `(Concept A, Concept B)` where Concept A is always taught _before_ Concept B in the syllabus. This chronological constraint drastically reduces the search space compared to pairing every topic with every other topic.

### Phase 3: Feature Engineering

To allow a machine learning model to evaluate these pairs, we extract three key mathematical signals (features):

1. **`embedding_similarity`**: We use a pre-trained NLP model (Sentence-Transformer `all-MiniLM-L6-v2`) to convert concepts into 384-dimensional dense vectors and compute their Cosine Similarity. This captures semantic meaning (e.g., "Neural Nets" is conceptually close to "Deep Learning").
2. **`keyword_overlap`**: The Jaccard similarity of exact words shared between two concepts.
3. **`order_delta`**: The physical distance between the two topics in the syllabus sequence.

### Phase 4: Ground Truth Bootstrapping

Because no large-scale, labeled dataset of engineering prerequisites exists, we bootstrapped our own. We applied strict heuristic rules (e.g., very high similarity + very high keyword overlap) to automatically label pairs as `1` (Prerequisite) or `0` (Not Prerequisite). Crucially, these labels were then **audited and corrected by human reviewers** to remove false positives and ensure the dataset acts as a high-quality "Ground Truth."

### Phase 5: Machine Learning Classification

We trained an XGBoost classifier on this dataset. At runtime, when given a brand new syllabus, the system computes the features for all chronological pairs, passes them through the trained XGBoost model, and any pair scoring above our decision threshold is added as a directed edge in the Knowledge Graph.

---

## 3. The Final Output: DAG & Kahn's Algorithm

Once the Machine Learning model predicts all the prerequisite relationships, the system constructs a **DAG (Directed Acyclic Graph)**.

- **Why a DAG?** The graph must be strictly "Acyclic" (meaning no loops). Learning paths cannot have circular dependencies (e.g., you can't require Concept A to learn Concept B, _and_ require Concept B to learn Concept A). The DAG mathematically enforces a logical, top-down curriculum.

To generate the actual step-by-step study sequence for a student, the backend runs **Kahn's Algorithm (Topological Sort)** on this DAG.

- **How Kahn's Algorithm works here:** It calculates the "in-degree" (number of missing prerequisites) for every topic. It starts by outputting topics with an in-degree of 0 (can be learned immediately). As those are added to the sequence, it removes their outward edges, lowering the in-degree of advanced topics until they hit 0 and become ready to learn. This guarantees a mathematically optimal study path where no concept is ever introduced before its prerequisites are met.

---

## 4. Anticipated Questions & How to Defend Them

### Q1: Why did you use XGBoost? Why not Logistic Regression, SVM, or Deep Learning?

**The Defense:**
We actually started with a Logistic Regression baseline, but prerequisite logic involves complex, non-linear interactions. For instance, a high `order_delta` might mean two topics are unrelated, _unless_ they also share a high `keyword_overlap`.

- **Vs. Linear Models:** Logistic Regression struggles with these non-linear feature interactions.
- **Vs. Deep Learning:** Neural networks are notoriously data-hungry and prone to severe overfitting on smaller tabular datasets (our dataset is ~1,100 rows).
- **The Choice:** XGBoost (Extreme Gradient Boosting) is the industry standard for tabular data of this size. It naturally captures non-linear interactions through decision trees, handles imbalanced data beautifully, and is highly resistant to overfitting compared to neural networks.

### Q2: Why use a local "Sentence-Transformer" instead of Large Language Models (like GPT-4) for the whole thing?

**The Defense:**
Scalability, cost, and determinism. Running an LLM to evaluate thousands of candidate pairs per syllabus is extremely slow and incurs massive API costs. By using a lightweight local embedding model (`all-MiniLM-L6-v2`), we can compute semantic similarities in milliseconds on standard CPU hardware with zero API costs, making the pipeline instantly scalable to thousands of PDFs.

### Q3: Why is your decision threshold set to 0.20 instead of the standard 0.50?

**The Defense:**
In classification, 0.50 is just an arbitrary mathematical default. Because our initial training labels were strictly audited to eliminate false positives, our XGBoost model learned to be hyper-conservative. At 0.50, our Precision was 100%, but our Recall was too low (it was missing valid prerequisites).
We performed an empirical **Threshold Sweep** on a blinded Validation set. We mathematically proved that lowering the threshold to 0.20 maximized our Recall (jumping from 73% to 93%) while strictly maintaining our Precision constraint (keeping it above 90%).

### Q4: How do you know the model isn't just memorizing specific Computer Science terms?

**The Defense:**
We implemented strict **concept-aware dataset splitting**. If "Machine Learning" appears in our Training set, our code guarantees it will _never_ appear in our Validation or Test sets. This prevents data leakage.
Furthermore, we maintain a completely isolated **Cross-Domain Test Set** containing syllabi from entirely different engineering branches (like Mechanical and Electrical) to explicitly measure and improve the model's ability to generalize true prerequisite logic, rather than just memorizing vocabulary.
