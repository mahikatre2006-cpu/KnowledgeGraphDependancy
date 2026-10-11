import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

df = pd.read_csv("DATA/review/extraction_pilot_v2.csv")

print("="*90)
print("COMPREHENSIVE AUDIT OF ALL 196 TOPICS: SUSPECT TOPIC CLASSIFICATION")
print("="*90)

# Define suspect evaluation rules
suspects = []

for idx, r in df.iterrows():
    c = r['course_code']
    u = r['unit']
    name = r['topic_name']
    quote = r['source_quote']
    page = r['page']
    
    # 1. XML / JSON check
    if name in ["XML Introduction", "JSON Introduction", "JSON"]:
        if name == "JSON":
            suspects.append({
                "course": c, "module": u, "topic": name, "quote": quote, "page": page,
                "reason": "Repeated concept: 'JSON Introduction' already extracted in Module I. Appears here under Self-learning Topics.",
                "classification": "probable over-split"
            })
        elif name in ["XML Introduction", "JSON Introduction"]:
            suspects.append({
                "course": c, "module": u, "topic": name, "quote": quote, "page": page,
                "reason": "Data format introduction: XML and JSON are distinct serialization formats listed separately ('XML introduction, Json introduction').",
                "classification": "legitimate distinct concept"
            })

    # 2. ITC501 Module II elementary syntax tokens
    elif c == "ITC501" and "Module II" in u and name in ["Variables", "Condition", "Loops", "Functions"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Elementary syntax constructs extracted as standalone prerequisite topics in Sem V (Internet Programming). Very low pedagogical granularity.",
            "classification": "uncertain"
        })
        
    # 3. ITC501 Module III setup & generic items
    elif c == "ITC501" and "Module III" in u and name in ["Installation", "Installing Libraries"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Basic environment setup actions rather than foundational conceptual knowledge entities.",
            "classification": "probable over-split"
        })
    elif c == "ITC501" and "Module III" in u and name in ["Folder Structure", "File Structure"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Split from single phrase 'Folder and file structure'. Represents the same project scaffolding concept.",
            "classification": "probable over-split"
        })
    elif c == "ITC501" and "Module III" in u and name in ["UI Design", "Animations", "Best Practices"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Broad software design/styling descriptors rather than specific React architectural concepts.",
            "classification": "uncertain"
        })
    elif c == "ITC501" and "Module III" in u and name == "React vs Angular vs Vue":
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Framework comparison from Self-learning section. Evaluative topic rather than core functional prerequisite.",
            "classification": "uncertain"
        })

    # 4. 2113112 Module I Set sub-variants
    elif c == "2113112" and "Crisp Set Theory" in u and name in ["Universal Sets", "Empty Sets"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Split from 'Universal and Empty Sets'. Both are basic boundary types subsumed under 'Sets' and 'Subsets'.",
            "classification": "uncertain"
        })
    elif c == "2113112" and "Crisp Set Theory" in u and name in ["Proof by Deduction", "Proof by Cases", "Proof by Exhaustion"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Minor proof technique variants extracted alongside core proof methods (Direct, Contradiction, Counterexample, Induction).",
            "classification": "uncertain"
        })

    # 5. 2113112 Module II Lattice & Poset sub-variants
    elif c == "2113112" and "Mathematical Relations" in u and name in ["Chain", "Anti Chains"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Split from 'Chain and Anti chains'. Chains (totally ordered) and antichains (incomparable) are dual poset concepts.",
            "classification": "legitimate distinct concept"
        })
    elif c == "2113112" and "Mathematical Relations" in u and name in ["Types of Lattices", "Sublattice"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Taxonomic classifications and sub-structures of Lattice. Closely related to 'Lattice'.",
            "classification": "legitimate distinct concept"
        })

    # 6. 2113112 Module VI Graph Theory suspect topics
    elif c == "2113112" and "Graph Theory" in u and name in ["Walk", "Path", "Circuit"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Formally distinct graph traversal concepts. Human reviewer explicitly demanded splitting them (row 36 note: 'split them').",
            "classification": "legitimate distinct concept"
        })
    elif c == "2113112" and "Graph Theory" in u and name in ["Connected Graphs", "Disconnected Graph", "Graph Components"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Topological connectivity properties vs maximal connected subgraphs. Explicitly enumerated.",
            "classification": "legitimate distinct concept"
        })
    elif c == "2113112" and "Graph Theory" in u and name in ["Euler Graphs", "Hamiltonian Graphs"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Distinct graph traversals (Eulerian trail vs Hamiltonian cycle). Human reviewer explicitly demanded splitting them (row 38).",
            "classification": "legitimate distinct concept"
        })
    elif c == "2113112" and "Graph Theory" in u and name in ["Homomorphism of Graphs", "Isomorphism of Graphs"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Distinct algebraic graph mappings. Human reviewer explicitly demanded splitting them (row 37).",
            "classification": "legitimate distinct concept"
        })
    elif c == "2113112" and "Graph Theory" in u and name in ["Cut Set", "Cut Vertex"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Edge disconnection set vs vertex cut point. Human reviewer explicitly demanded splitting them (row 39).",
            "classification": "legitimate distinct concept"
        })

    # 7. CSC303 suspect topics
    elif c == "CSC303" and name in ["Linear Data Structures", "Nonlinear Data Structures"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Broad taxonomy of data structures. Human reviewer explicitly demanded splitting them (row 18).",
            "classification": "legitimate distinct concept"
        })
    elif c == "CSC303" and name in ["Stack using Singly Linked List", "Queue using Singly Linked List"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Separate linear ADT implementations on linked lists. Human reviewer explicitly demanded splitting them (row 20).",
            "classification": "legitimate distinct concept"
        })
    elif c == "CSC303" and name in ["Polynomial Representation", "Polynomial Addition"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Linked list application: representation data structure vs arithmetic operation algorithm. Human reviewer demanded split (row 21).",
            "classification": "legitimate distinct concept"
        })
    elif c == "CSC303" and name in ["Linear Search", "Binary Search"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Sequential vs logarithmic search algorithms. Human reviewer demanded split (row 25).",
            "classification": "legitimate distinct concept"
        })
    elif c == "CSC303" and name in ["Hashing Concept", "Hash Functions"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "General hashing paradigm vs mathematical mapping functions. Human reviewer demanded split (row 26).",
            "classification": "legitimate distinct concept"
        })
    elif c == "CSC303" and name in ["Rotations in AVL Tree", "Operations on AVL Tree"]:
        suspects.append({
            "course": c, "module": u, "topic": name, "quote": quote, "page": page,
            "reason": "Balancing re-structuring primitive vs higher-level insert/delete operations. Human reviewer demanded split (row 22).",
            "classification": "legitimate distinct concept"
        })

print(f"Total suspects audited: {len(suspects)}")

# Group by classification
for cat in ["probable over-split", "uncertain", "legitimate distinct concept"]:
    cat_items = [s for s in suspects if s['classification'] == cat]
    print(f"\n==================================================")
    print(f"CLASSIFICATION: {cat.upper()} ({len(cat_items)} topics)")
    print(f"==================================================")
    for idx, s in enumerate(cat_items, 1):
        print(f"{idx:>2}. [{s['course']}] [{s['module']}] '{s['topic']}'")
        print(f"    Source Quote: '{s['quote']}' (p. {s['page']})")
        print(f"    Concern     : {s['reason']}")

