# backend/scripts/seed_mu_graph.py
"""
Seeds the Supabase `concept_clusters` table with the Mumbai University
Engineering Truth Layer — hardcoded, curated concepts for F.E. (Sem 1-2)
and S.E. IT pillars (DBMS, DSA, OOP).

Usage:
    cd backend
    python -m scripts.seed_mu_graph
"""

import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from supabase import create_client, Client

# ============================================================
# Supabase Client
# ============================================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("🚨 Missing SUPABASE_URL or SUPABASE_KEY in .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# Truth Layer Data — Mumbai University Engineering
# ============================================================

# Each entry: (concept_name, branch, subject, semester, module_number, difficulty_tier, parent_key)
# parent_key is a (concept_name, subject) tuple or None

CONCEPTS: list[dict] = []

def _add(concept_name: str, branch: str, subject: str, semester: int,
         module_number: int = None, difficulty_tier: str = "foundational",
         parent_key: tuple = None):
    """Helper to build concept entries."""
    CONCEPTS.append({
        "concept_name": concept_name,
        "branch": branch,
        "subject": subject,
        "semester": semester,
        "module_number": module_number,
        "difficulty_tier": difficulty_tier,
        "_parent_key": parent_key,  # resolved after insert
    })


# ----------------------------------------------------------
# F.E. Semester 1 — Engineering Mathematics I
# ----------------------------------------------------------
_add("Complex Numbers", "Core", "Engineering Mathematics I", 1, 1, "foundational")
_add("Polar & Exponential Forms", "Core", "Engineering Mathematics I", 1, 1, "foundational", ("Complex Numbers", "Engineering Mathematics I"))
_add("De Moivre's Theorem", "Core", "Engineering Mathematics I", 1, 1, "intermediate", ("Complex Numbers", "Engineering Mathematics I"))
_add("Hyperbolic Functions", "Core", "Engineering Mathematics I", 1, 1, "intermediate")
_add("Matrices & Determinants", "Core", "Engineering Mathematics I", 1, 2, "foundational")
_add("Eigenvalues & Eigenvectors", "Core", "Engineering Mathematics I", 1, 2, "intermediate", ("Matrices & Determinants", "Engineering Mathematics I"))
_add("Cayley-Hamilton Theorem", "Core", "Engineering Mathematics I", 1, 2, "advanced", ("Eigenvalues & Eigenvectors", "Engineering Mathematics I"))
_add("Differential Calculus", "Core", "Engineering Mathematics I", 1, 3, "foundational")
_add("Successive Differentiation", "Core", "Engineering Mathematics I", 1, 3, "intermediate", ("Differential Calculus", "Engineering Mathematics I"))
_add("Leibnitz's Theorem", "Core", "Engineering Mathematics I", 1, 3, "intermediate", ("Successive Differentiation", "Engineering Mathematics I"))
_add("Partial Differentiation", "Core", "Engineering Mathematics I", 1, 4, "intermediate")
_add("Euler's Theorem (Homogeneous)", "Core", "Engineering Mathematics I", 1, 4, "advanced", ("Partial Differentiation", "Engineering Mathematics I"))
_add("Integration Techniques", "Core", "Engineering Mathematics I", 1, 5, "foundational")
_add("Beta & Gamma Functions", "Core", "Engineering Mathematics I", 1, 5, "intermediate", ("Integration Techniques", "Engineering Mathematics I"))
_add("Double & Triple Integrals", "Core", "Engineering Mathematics I", 1, 6, "advanced", ("Integration Techniques", "Engineering Mathematics I"))

# ----------------------------------------------------------
# F.E. Semester 1 — Engineering Physics
# ----------------------------------------------------------
_add("Crystal Structure", "Core", "Engineering Physics", 1, 1, "foundational")
_add("Miller Indices", "Core", "Engineering Physics", 1, 1, "intermediate", ("Crystal Structure", "Engineering Physics"))
_add("Wave Optics", "Core", "Engineering Physics", 1, 2, "foundational")
_add("Interference & Diffraction", "Core", "Engineering Physics", 1, 2, "intermediate", ("Wave Optics", "Engineering Physics"))
_add("Quantum Mechanics Basics", "Core", "Engineering Physics", 1, 3, "intermediate")
_add("Schrödinger Wave Equation", "Core", "Engineering Physics", 1, 3, "advanced", ("Quantum Mechanics Basics", "Engineering Physics"))
_add("Semiconductor Physics", "Core", "Engineering Physics", 1, 4, "foundational")
_add("PN Junction & Diodes", "Core", "Engineering Physics", 1, 4, "intermediate", ("Semiconductor Physics", "Engineering Physics"))

# ----------------------------------------------------------
# F.E. Semester 1 — Engineering Chemistry
# ----------------------------------------------------------
_add("Water Treatment", "Core", "Engineering Chemistry", 1, 1, "foundational")
_add("Hardness & Softening", "Core", "Engineering Chemistry", 1, 1, "intermediate", ("Water Treatment", "Engineering Chemistry"))
_add("Corrosion Science", "Core", "Engineering Chemistry", 1, 2, "foundational")
_add("Types of Corrosion", "Core", "Engineering Chemistry", 1, 2, "intermediate", ("Corrosion Science", "Engineering Chemistry"))
_add("Polymers", "Core", "Engineering Chemistry", 1, 3, "foundational")
_add("Fuels & Combustion", "Core", "Engineering Chemistry", 1, 4, "foundational")
_add("Calorific Value Calculations", "Core", "Engineering Chemistry", 1, 4, "intermediate", ("Fuels & Combustion", "Engineering Chemistry"))

# ----------------------------------------------------------
# F.E. Semester 2 — Engineering Mathematics II
# ----------------------------------------------------------
_add("Ordinary Differential Equations", "Core", "Engineering Mathematics II", 2, 1, "foundational")
_add("First Order ODE", "Core", "Engineering Mathematics II", 2, 1, "foundational", ("Ordinary Differential Equations", "Engineering Mathematics II"))
_add("Higher Order Linear ODE", "Core", "Engineering Mathematics II", 2, 1, "intermediate", ("First Order ODE", "Engineering Mathematics II"))
_add("Laplace Transforms", "Core", "Engineering Mathematics II", 2, 2, "intermediate")
_add("Inverse Laplace Transforms", "Core", "Engineering Mathematics II", 2, 2, "intermediate", ("Laplace Transforms", "Engineering Mathematics II"))
_add("Fourier Series", "Core", "Engineering Mathematics II", 2, 3, "intermediate")
_add("Half Range Expansions", "Core", "Engineering Mathematics II", 2, 3, "advanced", ("Fourier Series", "Engineering Mathematics II"))
_add("Vector Calculus", "Core", "Engineering Mathematics II", 2, 4, "foundational")
_add("Gradient, Divergence, Curl", "Core", "Engineering Mathematics II", 2, 4, "intermediate", ("Vector Calculus", "Engineering Mathematics II"))
_add("Line & Surface Integrals", "Core", "Engineering Mathematics II", 2, 5, "advanced", ("Vector Calculus", "Engineering Mathematics II"))

# ----------------------------------------------------------
# F.E. Semester 2 — Basic Electrical Engineering (BEE)
# ----------------------------------------------------------
_add("DC Circuit Analysis", "Core", "Basic Electrical Engineering", 2, 1, "foundational")
_add("Kirchhoff's Laws (KVL/KCL)", "Core", "Basic Electrical Engineering", 2, 1, "foundational", ("DC Circuit Analysis", "Basic Electrical Engineering"))
_add("Network Theorems", "Core", "Basic Electrical Engineering", 2, 2, "intermediate", ("DC Circuit Analysis", "Basic Electrical Engineering"))
_add("AC Fundamentals", "Core", "Basic Electrical Engineering", 2, 3, "foundational")
_add("Phasor Diagrams", "Core", "Basic Electrical Engineering", 2, 3, "intermediate", ("AC Fundamentals", "Basic Electrical Engineering"))
_add("Transformers", "Core", "Basic Electrical Engineering", 2, 4, "intermediate")
_add("Three Phase Systems", "Core", "Basic Electrical Engineering", 2, 5, "advanced")

# ----------------------------------------------------------
# F.E. Semester 2 — Programming (C / Python)
# ----------------------------------------------------------
_add("Variables & Data Types", "Core", "Programming Fundamentals", 2, 1, "foundational")
_add("Control Flow (if/else/loops)", "Core", "Programming Fundamentals", 2, 1, "foundational", ("Variables & Data Types", "Programming Fundamentals"))
_add("Functions", "Core", "Programming Fundamentals", 2, 2, "foundational", ("Control Flow (if/else/loops)", "Programming Fundamentals"))
_add("Arrays & Strings", "Core", "Programming Fundamentals", 2, 2, "foundational")
_add("Pointers (C)", "Core", "Programming Fundamentals", 2, 3, "intermediate", ("Variables & Data Types", "Programming Fundamentals"))
_add("Structures & Unions (C)", "Core", "Programming Fundamentals", 2, 3, "intermediate", ("Pointers (C)", "Programming Fundamentals"))
_add("File I/O", "Core", "Programming Fundamentals", 2, 4, "intermediate")
_add("Recursion", "Core", "Programming Fundamentals", 2, 4, "intermediate", ("Functions", "Programming Fundamentals"))

# ----------------------------------------------------------
# S.E. Semester 3 — Data Structures & Algorithms (DSA)
# ----------------------------------------------------------
_add("Algorithm Analysis", "Computing", "Data Structures & Algorithms", 3, 1, "foundational")
_add("Time Complexity (Big-O)", "Computing", "Data Structures & Algorithms", 3, 1, "foundational", ("Algorithm Analysis", "Data Structures & Algorithms"))
_add("Space Complexity", "Computing", "Data Structures & Algorithms", 3, 1, "foundational", ("Algorithm Analysis", "Data Structures & Algorithms"))
_add("Arrays", "Computing", "Data Structures & Algorithms", 3, 2, "foundational")
_add("Linked Lists", "Computing", "Data Structures & Algorithms", 3, 2, "foundational")
_add("Singly Linked List", "Computing", "Data Structures & Algorithms", 3, 2, "foundational", ("Linked Lists", "Data Structures & Algorithms"))
_add("Doubly Linked List", "Computing", "Data Structures & Algorithms", 3, 2, "intermediate", ("Linked Lists", "Data Structures & Algorithms"))
_add("Stacks", "Computing", "Data Structures & Algorithms", 3, 3, "foundational")
_add("Stack Applications (Infix/Postfix)", "Computing", "Data Structures & Algorithms", 3, 3, "intermediate", ("Stacks", "Data Structures & Algorithms"))
_add("Queues", "Computing", "Data Structures & Algorithms", 3, 3, "foundational")
_add("Circular Queue", "Computing", "Data Structures & Algorithms", 3, 3, "intermediate", ("Queues", "Data Structures & Algorithms"))
_add("Priority Queue", "Computing", "Data Structures & Algorithms", 3, 3, "intermediate", ("Queues", "Data Structures & Algorithms"))
_add("Trees", "Computing", "Data Structures & Algorithms", 3, 4, "intermediate")
_add("Binary Tree", "Computing", "Data Structures & Algorithms", 3, 4, "intermediate", ("Trees", "Data Structures & Algorithms"))
_add("Binary Search Tree", "Computing", "Data Structures & Algorithms", 3, 4, "intermediate", ("Binary Tree", "Data Structures & Algorithms"))
_add("AVL Tree", "Computing", "Data Structures & Algorithms", 3, 4, "advanced", ("Binary Search Tree", "Data Structures & Algorithms"))
_add("Tree Traversals (In/Pre/Post)", "Computing", "Data Structures & Algorithms", 3, 4, "intermediate", ("Binary Tree", "Data Structures & Algorithms"))
_add("Graphs", "Computing", "Data Structures & Algorithms", 3, 5, "intermediate")
_add("BFS & DFS", "Computing", "Data Structures & Algorithms", 3, 5, "intermediate", ("Graphs", "Data Structures & Algorithms"))
_add("Dijkstra's Algorithm", "Computing", "Data Structures & Algorithms", 3, 5, "advanced", ("Graphs", "Data Structures & Algorithms"))
_add("Minimum Spanning Tree", "Computing", "Data Structures & Algorithms", 3, 5, "advanced", ("Graphs", "Data Structures & Algorithms"))
_add("Sorting Algorithms", "Computing", "Data Structures & Algorithms", 3, 6, "foundational")
_add("Bubble/Selection/Insertion Sort", "Computing", "Data Structures & Algorithms", 3, 6, "foundational", ("Sorting Algorithms", "Data Structures & Algorithms"))
_add("Merge Sort", "Computing", "Data Structures & Algorithms", 3, 6, "intermediate", ("Sorting Algorithms", "Data Structures & Algorithms"))
_add("Quick Sort", "Computing", "Data Structures & Algorithms", 3, 6, "intermediate", ("Sorting Algorithms", "Data Structures & Algorithms"))
_add("Hashing", "Computing", "Data Structures & Algorithms", 3, 7, "intermediate")
_add("Collision Resolution", "Computing", "Data Structures & Algorithms", 3, 7, "intermediate", ("Hashing", "Data Structures & Algorithms"))

# ----------------------------------------------------------
# S.E. Semester 3 — Database Management Systems (DBMS)
# ----------------------------------------------------------
_add("Introduction to DBMS", "Computing", "Database Management Systems", 3, 1, "foundational")
_add("Data Models (ER Model)", "Computing", "Database Management Systems", 3, 1, "foundational", ("Introduction to DBMS", "Database Management Systems"))
_add("ER Diagrams", "Computing", "Database Management Systems", 3, 1, "foundational", ("Data Models (ER Model)", "Database Management Systems"))
_add("Relational Algebra", "Computing", "Database Management Systems", 3, 2, "intermediate")
_add("SQL Fundamentals", "Computing", "Database Management Systems", 3, 2, "foundational")
_add("SQL Joins", "Computing", "Database Management Systems", 3, 2, "intermediate", ("SQL Fundamentals", "Database Management Systems"))
_add("SQL Aggregation & Subqueries", "Computing", "Database Management Systems", 3, 2, "intermediate", ("SQL Fundamentals", "Database Management Systems"))
_add("Normalization", "Computing", "Database Management Systems", 3, 3, "intermediate")
_add("1NF, 2NF, 3NF", "Computing", "Database Management Systems", 3, 3, "intermediate", ("Normalization", "Database Management Systems"))
_add("BCNF", "Computing", "Database Management Systems", 3, 3, "advanced", ("1NF, 2NF, 3NF", "Database Management Systems"))
_add("Functional Dependencies", "Computing", "Database Management Systems", 3, 3, "intermediate", ("Normalization", "Database Management Systems"))
_add("Transaction Management", "Computing", "Database Management Systems", 3, 4, "intermediate")
_add("ACID Properties", "Computing", "Database Management Systems", 3, 4, "foundational", ("Transaction Management", "Database Management Systems"))
_add("Concurrency Control", "Computing", "Database Management Systems", 3, 4, "advanced", ("Transaction Management", "Database Management Systems"))
_add("Deadlock Handling", "Computing", "Database Management Systems", 3, 4, "advanced", ("Concurrency Control", "Database Management Systems"))
_add("Indexing", "Computing", "Database Management Systems", 3, 5, "intermediate")
_add("B-Tree & B+ Tree", "Computing", "Database Management Systems", 3, 5, "advanced", ("Indexing", "Database Management Systems"))

# ----------------------------------------------------------
# S.E. Semester 3 — Object Oriented Programming (OOP)
# ----------------------------------------------------------
_add("Classes & Objects", "Computing", "Object Oriented Programming", 3, 1, "foundational")
_add("Constructors & Destructors", "Computing", "Object Oriented Programming", 3, 1, "foundational", ("Classes & Objects", "Object Oriented Programming"))
_add("Encapsulation", "Computing", "Object Oriented Programming", 3, 2, "foundational")
_add("Access Modifiers", "Computing", "Object Oriented Programming", 3, 2, "foundational", ("Encapsulation", "Object Oriented Programming"))
_add("Inheritance", "Computing", "Object Oriented Programming", 3, 3, "intermediate")
_add("Single & Multiple Inheritance", "Computing", "Object Oriented Programming", 3, 3, "intermediate", ("Inheritance", "Object Oriented Programming"))
_add("Polymorphism", "Computing", "Object Oriented Programming", 3, 4, "intermediate")
_add("Method Overloading", "Computing", "Object Oriented Programming", 3, 4, "intermediate", ("Polymorphism", "Object Oriented Programming"))
_add("Method Overriding", "Computing", "Object Oriented Programming", 3, 4, "intermediate", ("Polymorphism", "Object Oriented Programming"))
_add("Operator Overloading", "Computing", "Object Oriented Programming", 3, 4, "intermediate", ("Polymorphism", "Object Oriented Programming"))
_add("Abstraction", "Computing", "Object Oriented Programming", 3, 5, "intermediate")
_add("Abstract Classes", "Computing", "Object Oriented Programming", 3, 5, "intermediate", ("Abstraction", "Object Oriented Programming"))
_add("Interfaces", "Computing", "Object Oriented Programming", 3, 5, "intermediate", ("Abstraction", "Object Oriented Programming"))
_add("Exception Handling", "Computing", "Object Oriented Programming", 3, 6, "intermediate")
_add("File Handling (OOP)", "Computing", "Object Oriented Programming", 3, 6, "intermediate")
_add("Templates & Generics", "Computing", "Object Oriented Programming", 3, 7, "advanced")
_add("Design Patterns (Intro)", "Computing", "Object Oriented Programming", 3, 7, "advanced")
_add("Singleton Pattern", "Computing", "Object Oriented Programming", 3, 7, "advanced", ("Design Patterns (Intro)", "Object Oriented Programming"))
_add("Factory Pattern", "Computing", "Object Oriented Programming", 3, 7, "advanced", ("Design Patterns (Intro)", "Object Oriented Programming"))


# ============================================================
# Seeding Logic
# ============================================================

def seed():
    """Insert all concepts into Supabase with parent linking."""
    print(f"🌱 Seeding {len(CONCEPTS)} concepts into concept_clusters...")

    # Phase 1: Insert all concepts (without parent links)
    inserted_map: dict[tuple, str] = {}  # (concept_name, subject) -> UUID

    for concept in CONCEPTS:
        row = {
            "concept_name": concept["concept_name"],
            "branch": concept["branch"],
            "subject": concept["subject"],
            "semester": concept["semester"],
            "module_number": concept["module_number"],
            "difficulty_tier": concept["difficulty_tier"],
        }

        try:
            response = supabase.table("concept_clusters").upsert(
                row,
                on_conflict="concept_name,subject,semester"
            ).execute()

            if response.data and len(response.data) > 0:
                row_id = response.data[0]["id"]
                key = (concept["concept_name"], concept["subject"])
                inserted_map[key] = row_id
                print(f"  ✅ {concept['concept_name']} ({concept['subject']})")
            else:
                print(f"  ⚠️ No data returned for: {concept['concept_name']}")
        except Exception as e:
            print(f"  ❌ Failed: {concept['concept_name']} — {e}")

    # Phase 2: Link parent_concept_id
    print(f"\n🔗 Linking parent concepts...")
    link_count = 0

    for concept in CONCEPTS:
        parent_key = concept.get("_parent_key")
        if not parent_key:
            continue

        child_key = (concept["concept_name"], concept["subject"])
        child_id = inserted_map.get(child_key)
        parent_id = inserted_map.get(parent_key)

        if child_id and parent_id:
            try:
                supabase.table("concept_clusters").update(
                    {"parent_concept_id": parent_id}
                ).eq("id", child_id).execute()
                link_count += 1
            except Exception as e:
                print(f"  ❌ Link failed: {concept['concept_name']} → {parent_key[0]} — {e}")

    print(f"\n🎉 Seeding complete! {len(inserted_map)} concepts inserted, {link_count} parent links created.")


if __name__ == "__main__":
    seed()
