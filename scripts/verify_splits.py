"""
verify_splits.py
================
Phase D: Concept-Disjoint Split Verification

Partitions Cleaned_Files/labeling_dataset_cleaned.csv into:
  - Train: ~70%
  - Val:   ~10%
  - Test:  ~20%

Enforces strict concept-disjointness:
  Concepts(Train) ∩ Concepts(Test) = ∅
  Concepts(Train) ∩ Concepts(Val)  = ∅
  Concepts(Val)   ∩ Concepts(Test) = ∅

Any concept present in one partition is guaranteed to never appear
in any other partition, preventing data leakage across splits.
"""

import sys
import os
import csv
import json
import random
from pathlib import Path
from collections import defaultdict, deque, Counter

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_CSV    = PROJECT_ROOT / "Cleaned_Files" / "labeling_dataset_cleaned.csv"
OUT_DIR      = PROJECT_ROOT / "Cleaned_Files"
TRAIN_CSV    = OUT_DIR / "train_split.csv"
VAL_CSV      = OUT_DIR / "val_split.csv"
TEST_CSV     = OUT_DIR / "test_split.csv"
REPORT_JSON  = OUT_DIR / "split_verification_report.json"

RANDOM_SEED = 42


def get_concepts(row: dict) -> tuple[str, str]:
    return row["concept_a"].strip(), row["concept_b"].strip()


def build_concept_components(rows: list[dict]):
    adj = defaultdict(set)
    for r in rows:
        ca, cb = get_concepts(r)
        adj[ca].add(cb)
        adj[cb].add(ca)

    visited = set()
    components = []

    for node in sorted(adj.keys()):
        if node not in visited:
            comp_nodes = set()
            q = deque([node])
            visited.add(node)
            while q:
                curr = q.popleft()
                comp_nodes.add(curr)
                for nbr in sorted(adj[curr]):
                    if nbr not in visited:
                        visited.add(nbr)
                        q.append(nbr)
            
            comp_edges = [r for r in rows if r["concept_a"].strip() in comp_nodes]
            pos = sum(1 for r in comp_edges if r.get("label", "").strip() == "1")
            neg = sum(1 for r in comp_edges if r.get("label", "").strip() == "0")
            components.append({
                "nodes": sorted(comp_nodes),
                "edges": comp_edges,
                "pos": pos,
                "neg": neg,
                "total": len(comp_edges)
            })

    return components


def optimize_splits(components: list[dict], total_rows: int, seed: int = 42):
    rng = random.Random(seed)
    target_train = 0.70 * total_rows
    target_val   = 0.10 * total_rows
    target_test  = 0.20 * total_rows

    best_loss = 1e12
    best_assignment = None

    # Search for optimal component partition satisfying ratio + class coverage
    for _ in range(50000):
        train_c, val_c, test_c = [], [], []
        for c in components:
            r = rng.random()
            if r < 0.70:
                train_c.append(c)
            elif r < 0.80:
                val_c.append(c)
            else:
                test_c.append(c)

        nt = sum(c["total"] for c in train_c)
        nv = sum(c["total"] for c in val_c)
        nte = sum(c["total"] for c in test_c)

        pt = sum(c["pos"] for c in train_c)
        pv = sum(c["pos"] for c in val_c)
        pte = sum(c["pos"] for c in test_c)

        # Both val and test should have at least 1 positive and negative if possible
        if nt == 0 or nv == 0 or nte == 0:
            continue
        if pv == 0 or pte == 0 or (nv - pv) == 0 or (nte - pte) == 0:
            continue

        loss = ((nt - target_train) ** 2) + 3 * ((nv - target_val) ** 2) + 2 * ((nte - target_test) ** 2)
        if loss < best_loss:
            best_loss = loss
            best_assignment = (train_c, val_c, test_c)

    if best_assignment is None:
        raise RuntimeError("Failed to find valid concept-disjoint split satisfying constraints.")

    return best_assignment


def verify_disjointness(train_rows: list[dict], val_rows: list[dict], test_rows: list[dict]):
    train_concepts = set()
    for r in train_rows:
        ca, cb = get_concepts(r)
        train_concepts.update([ca, cb])

    val_concepts = set()
    for r in val_rows:
        ca, cb = get_concepts(r)
        val_concepts.update([ca, cb])

    test_concepts = set()
    for r in test_rows:
        ca, cb = get_concepts(r)
        test_concepts.update([ca, cb])

    train_val_leak = train_concepts & val_concepts
    train_test_leak = train_concepts & test_concepts
    val_test_leak = val_concepts & test_concepts

    return {
        "train_concepts_count": len(train_concepts),
        "val_concepts_count": len(val_concepts),
        "test_concepts_count": len(test_concepts),
        "train_val_overlap": sorted(list(train_val_leak)),
        "train_test_overlap": sorted(list(train_test_leak)),
        "val_test_overlap": sorted(list(val_test_leak)),
        "is_strictly_disjoint": (
            len(train_val_leak) == 0 and
            len(train_test_leak) == 0 and
            len(val_test_leak) == 0
        )
    }


def main():
    if not INPUT_CSV.exists():
        print(f"Error: {INPUT_CSV} not found.")
        sys.exit(1)

    with open(INPUT_CSV, encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    total_rows = len(rows)
    print(f"Loaded {total_rows} rows from {INPUT_CSV}")

    # 1. Build components
    components = build_concept_components(rows)
    print(f"Identified {len(components)} connected concept components.")

    # 2. Partition components
    train_comps, val_comps, test_comps = optimize_splits(components, total_rows, seed=RANDOM_SEED)

    train_rows = [r for c in train_comps for r in c["edges"]]
    val_rows   = [r for c in val_comps for r in c["edges"]]
    test_rows  = [r for c in test_comps for r in c["edges"]]

    # 3. Verify disjoint condition
    verification = verify_disjointness(train_rows, val_rows, test_rows)

    if not verification["is_strictly_disjoint"]:
        print("CRITICAL FAILURE: Concept leakage detected!")
        print("Train-Val overlap:", verification["train_val_overlap"])
        print("Train-Test overlap:", verification["train_test_overlap"])
        print("Val-Test overlap:", verification["val_test_overlap"])
        sys.exit(1)

    print("SUCCESS: Strict concept-disjointness verified! (Zero concept overlap across splits)")

    # 4. Write CSV splits
    for path, data in [(TRAIN_CSV, train_rows), (VAL_CSV, val_rows), (TEST_CSV, test_rows)]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"Wrote {len(data)} rows to {path}")

    # 5. Compile report
    def get_stats(data):
        lc = Counter(r.get("label", "").strip() for r in data)
        p = lc.get("1", 0)
        n = lc.get("0", 0)
        return {
            "rows": len(data),
            "percentage": round(len(data) / total_rows * 100, 2),
            "pos": p,
            "neg": n,
            "pos_ratio": round(p / len(data), 4) if data else 0
        }

    report = {
        "dataset_path": str(INPUT_CSV),
        "total_rows": total_rows,
        "connected_components": len(components),
        "splits": {
            "train": get_stats(train_rows),
            "val": get_stats(val_rows),
            "test": get_stats(test_rows),
        },
        "verification": verification
    }

    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Saved verification report to {REPORT_JSON}")

    # Print summary table
    print("\n" + "=" * 75)
    print(f"{'Split':<10} | {'Rows':<6} | {'% Total':<8} | {'Pos':<5} | {'Neg':<5} | {'Pos Ratio':<10} | {'Concepts':<8}")
    print("-" * 75)
    for name, s, c_cnt in [
        ("Train", report["splits"]["train"], verification["train_concepts_count"]),
        ("Val",   report["splits"]["val"],   verification["val_concepts_count"]),
        ("Test",  report["splits"]["test"],  verification["test_concepts_count"]),
    ]:
        print(f"{name:<10} | {s['rows']:<6} | {s['percentage']:<8.1f}% | {s['pos']:<5} | {s['neg']:<5} | {s['pos_ratio']:<10.1%} | {c_cnt:<8}")
    print("=" * 75)
    print(f"Train ∩ Val  Overlap : {len(verification['train_val_overlap'])} concepts")
    print(f"Train ∩ Test Overlap : {len(verification['train_test_overlap'])} concepts")
    print(f"Val   ∩ Test Overlap : {len(verification['val_test_overlap'])} concepts")
    print("=" * 75)


if __name__ == "__main__":
    main()

