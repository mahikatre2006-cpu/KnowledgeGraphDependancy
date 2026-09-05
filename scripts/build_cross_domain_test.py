"""
build_cross_domain_test.py
===========================
Generates 250 labeled concept pairs from non-IT engineering disciplines
(Mechanical Engineering, Civil Engineering, Electrical Engineering).

These rows NEVER enter training and serve as the held-out cross-domain evaluation set
specified in KDG PRD Section 4 and Retrofit Plan Phase R1.5.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import re

project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.services.embedding_service import LocalEmbeddingService

# Define representative topic sequences for non-IT departments
NON_IT_COURSES = {
    "MECH101": {
        "name": "Mechanical Engineering - Thermodynamics & Fluid Mechanics",
        "topics": [
            "Zeroth Law and Temperature", "First Law of Thermodynamics", "Internal Energy and Enthalpy",
            "Second Law and Heat Engines", "Entropy and Reversibility", "Carnot Cycle",
            "Properties of Pure Substances", "Steam Tables and Mollier Chart", "Rankine Cycle",
            "Fluid Statics and Pressure Measurement", "Buoyancy and Floatation", "Fluid Kinematics and Continuity",
            "Bernoulli Equation and Applications", "Viscous Flow in Pipes", "Boundary Layer Theory",
            "Laminar and Turbulent Flow", "Dimensional Analysis and Similitude", "Hydraulic Turbines and Pumps"
        ]
    },
    "CIVIL101": {
        "name": "Civil Engineering - Structural Analysis & Geotechnical",
        "topics": [
            "Stress and Strain Fundamentals", "Hooke Law and Elastic Constants", "Shear Force and Bending Moment",
            "Bending Stresses in Beams", "Shear Stresses in Beams", "Torsion of Circular Shafts",
            "Deflection of Beams", "Euler Column Theory", "Truss Analysis and Method of Joints",
            "Soil Composition and Phase Relations", "Index Properties and Soil Classification",
            "Permeability and Darcy Law", "Seepage Analysis and Flow Nets", "Compaction and Consolidation",
            "Mohr Coulomb Shear Strength", "Lateral Earth Pressure", "Bearing Capacity of Shallow Foundations"
        ]
    },
    "ELEC101": {
        "name": "Electrical Engineering - Circuit Theory & Analog Electronics",
        "topics": [
            "Ohm Law and Kirchhoff Laws", "Nodal and Mesh Analysis", "Superposition Theorem",
            "Thevenin and Norton Theorems", "Maximum Power Transfer Theorem", "RL and RC Transient Response",
            "Sinusoidal Steady State Analysis", "Phasors and Impedance", "Resonance in RLC Circuits",
            "Semiconductor Physics and Doping", "PN Junction Diode Characteristics", "Diode Rectifiers and Wave Shaping",
            "Zener Diode Voltage Regulators", "Bipolar Junction Transistor Biasing", "BJT Small Signal Analysis",
            "Field Effect Transistors", "Operational Amplifier Basics", "Inverting and Non-inverting Op-Amps"
        ]
    }
}

def keyword_overlap(a: str, b: str) -> float:
    sa = set(re.findall(r"\w+", a.lower()))
    sb = set(re.findall(r"\w+", b.lower()))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)

def main():
    print("Generating cross-domain test dataset for Non-IT subjects...")
    pairs = []

    for course_code, info in NON_IT_COURSES.items():
        topics = info["topics"]
        n = len(topics)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                delta = j - i
                # Consider candidate pairs with forward or small backward order
                if 1 <= delta <= 8:
                    concept_a = topics[i]
                    concept_b = topics[j]
                    
                    # Direct prerequisite definition:
                    # Concepts occurring earlier that are conceptual foundations for later concepts
                    # Close delta and foundational dependency
                    if delta <= 3:
                        label = 1
                    elif delta <= 6 and ("Law" in concept_a or "Fundamentals" in concept_a or "Basics" in concept_a or "Physics" in concept_a or "Stress and Strain" in concept_a):
                        label = 1
                    else:
                        label = 0
                        
                    pairs.append({
                        "concept_a": concept_a,
                        "concept_b": concept_b,
                        "Course_Code": course_code,
                        "source_syllabus": f"{course_code}.pdf",
                        "order_delta": delta,
                        "domain_match": 1,
                        "label": label
                    })
                elif delta > 8:
                    # Hard negatives far apart
                    pairs.append({
                        "concept_a": topics[i],
                        "concept_b": topics[j],
                        "Course_Code": course_code,
                        "source_syllabus": f"{course_code}.pdf",
                        "order_delta": delta,
                        "domain_match": 1,
                        "label": 0
                    })

    df = pd.DataFrame(pairs)
    # Balance to ~250 rows
    pos = df[df["label"] == 1]
    neg = df[df["label"] == 0]
    
    n_pos = min(len(pos), 100)
    n_neg = 150
    
    sampled_pos = pos.sample(n=n_pos, random_state=42)
    sampled_neg = neg.sample(n=n_neg, random_state=42)
    
    sampled = pd.concat([sampled_pos, sampled_neg]).sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Compute embeddings
    all_concepts = list(set(sampled["concept_a"].tolist() + sampled["concept_b"].tolist()))
    raw_emb = LocalEmbeddingService.encode_batch(all_concepts)
    norms = np.linalg.norm(raw_emb, axis=1, keepdims=True)
    norms[norms == 0] = 1e-10
    norm_emb = raw_emb / norms
    c2idx = {c: i for i, c in enumerate(all_concepts)}
    
    sims = []
    kws = []
    for _, row in sampled.iterrows():
        ia = c2idx[row["concept_a"]]
        ib = c2idx[row["concept_b"]]
        sim = float(np.dot(norm_emb[ia], norm_emb[ib]))
        sims.append(round(sim, 4))
        kws.append(round(keyword_overlap(row["concept_a"], row["concept_b"]), 4))
        
    sampled["embedding_similarity"] = sims
    sampled["keyword_overlap"] = kws
    
    out_cols = [
        "concept_a", "concept_b", "Course_Code", "source_syllabus",
        "embedding_similarity", "order_delta", "domain_match", "keyword_overlap", "label"
    ]
    sampled = sampled[out_cols]
    
    out_path = Path(project_root) / "data" / "cross_domain_test.csv"
    sampled.to_csv(out_path, index=False)
    print(f"Saved {len(sampled)} cross-domain test rows to {out_path}")
    print(f"Class distribution: {sampled['label'].value_counts().to_dict()}")

if __name__ == "__main__":
    main()

