import os
import sys
import json
import csv
import random
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.services.embedding_service import LocalEmbeddingService


def main():
    # 1. Load topics
    topics_file = Path("DATA/processed/topics_v5.json")
    assert topics_file.exists(), f"Missing {topics_file}"
    with open(topics_file, "r", encoding="utf-8") as f:
        courses_data = json.load(f)

    # 2. Load teacher edges
    edges_file = Path("DATA/processed/teacher_edges_v5.csv")
    assert edges_file.exists(), f"Missing {edges_file}"

    confident_edges = []
    uncertain_edges_set = set()
    confident_edges_set = set()

    with open(edges_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            course = row["course"]
            a_id = row["a_id"]
            b_id = row["b_id"]
            status = row["status"]
            if status == "confident":
                confident_edges.append(row)
                confident_edges_set.add((course, a_id, b_id))
            elif status == "uncertain":
                uncertain_edges_set.add((course, a_id, b_id))

    print(f"Loaded {len(confident_edges)} confident edges, {len(uncertain_edges_set)} uncertain edges.")

    # 3. Load old dataset to exclude ALL old rows
    old_dataset_path = Path("True_Cleaned_Dataset/final_training_dataset.csv")
    old_pairs = set()
    if old_dataset_path.exists():
        with open(old_dataset_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ca = row.get("concept_a", "").strip().lower()
                cb = row.get("concept_b", "").strip().lower()
                if ca and cb:
                    old_pairs.add((ca, cb))
    print(f"Loaded {len(old_pairs)} legacy concept pairs to exclude.")

    # Topic lookup per course: course -> id -> topic_dict
    topic_map = {}
    for code, cdata in courses_data.items():
        topic_map[code] = {t["id"]: t for t in cdata["topics"]}

    # 4. Form Positives
    positive_rows = []
    excluded_pos_old = 0
    for edge in confident_edges:
        course = edge["course"]
        a_id = edge["a_id"]
        b_id = edge["b_id"]
        t_a = topic_map[course][a_id]
        t_b = topic_map[course][b_id]

        pair_key = (t_a["name"].strip().lower(), t_b["name"].strip().lower())
        if pair_key in old_pairs:
            excluded_pos_old += 1
            continue

        positive_rows.append({
            "course": course,
            "a_id": a_id,
            "b_id": b_id,
            "a_name": t_a["name"],
            "b_name": t_b["name"],
            "pos_a": t_a["position"],
            "pos_b": t_b["position"],
            "unit_a": t_a["module_idx"],
            "unit_b": t_b["module_idx"],
            "n_topics": courses_data[course]["n_topics"],
            "label": 1,
            "neg_type": "positive",
        })

    print(f"Valid positive rows: {len(positive_rows)} (excluded {excluded_pos_old} from old dataset).")

    target_neg_count = 3 * len(positive_rows)
    print(f"Target negative count (3:1 ratio): {target_neg_count}")

    # Helper function to check if candidate pair is allowed as negative
    def is_valid_negative(course, a_id, b_id):
        if a_id == b_id:
            return False
        if (course, a_id, b_id) in confident_edges_set:
            return False
        if (course, a_id, b_id) in uncertain_edges_set:
            return False
        t_a = topic_map[course][a_id]
        t_b = topic_map[course][b_id]
        pair_key = (t_a["name"].strip().lower(), t_b["name"].strip().lower())
        if pair_key in old_pairs:
            return False
        return True

    # Target: 3 * len(positive_rows) = 2736
    # Balance across the 4 types:
    # 1. reversed_positive: all valid reversed positives (~911)
    # 2. adjacent_unlinked: sample ~700
    # 3. high_similarity_unlinked: sample ~700
    # 4. random_same_course: remaining to hit exactly target_neg_count (~425)
    rng = random.Random(42)

    negative_rows = []
    selected_neg_keys = set()

    # Neg Type 1: reversed positives (B -> A for confident A -> B)
    rev_candidates = []
    for pos in positive_rows:
        course = pos["course"]
        a_id = pos["b_id"]  # reversed
        b_id = pos["a_id"]
        if is_valid_negative(course, a_id, b_id) and (course, a_id, b_id) not in selected_neg_keys:
            rev_candidates.append((course, a_id, b_id))

    for course, a_id, b_id in rev_candidates:
        selected_neg_keys.add((course, a_id, b_id))
        t_a = topic_map[course][a_id]
        t_b = topic_map[course][b_id]
        negative_rows.append({
            "course": course,
            "a_id": a_id,
            "b_id": b_id,
            "a_name": t_a["name"],
            "b_name": t_b["name"],
            "pos_a": t_a["position"],
            "pos_b": t_b["position"],
            "unit_a": t_a["module_idx"],
            "unit_b": t_b["module_idx"],
            "n_topics": courses_data[course]["n_topics"],
            "label": 0,
            "neg_type": "reversed_positive",
        })
    print(f"Generated {len(negative_rows)} reversed_positive negatives.")

    # Neg Type 2: adjacent pairs not linked (target ~700)
    adj_candidates = []
    for code, cdata in courses_data.items():
        topics = cdata["topics"]
        for i in range(len(topics) - 1):
            t1, t2 = topics[i], topics[i + 1]
            for a_id, b_id in [(t1["id"], t2["id"]), (t2["id"], t1["id"])]:
                if is_valid_negative(code, a_id, b_id) and (code, a_id, b_id) not in selected_neg_keys:
                    adj_candidates.append((code, a_id, b_id))
    rng.shuffle(adj_candidates)
    adj_target = min(700, len(adj_candidates))
    for code, a_id, b_id in adj_candidates[:adj_target]:
        selected_neg_keys.add((code, a_id, b_id))
        t_a = topic_map[code][a_id]
        t_b = topic_map[code][b_id]
        negative_rows.append({
            "course": code,
            "a_id": a_id,
            "b_id": b_id,
            "a_name": t_a["name"],
            "b_name": t_b["name"],
            "pos_a": t_a["position"],
            "pos_b": t_b["position"],
            "unit_a": t_a["module_idx"],
            "unit_b": t_b["module_idx"],
            "n_topics": courses_data[code]["n_topics"],
            "label": 0,
            "neg_type": "adjacent_unlinked",
        })
    print(f"Generated {adj_target} adjacent_unlinked negatives.")

    # Neg Type 3: high-similarity unlinked pairs (target ~700)
    print("Computing embeddings for high-similarity negative mining...")
    high_sim_candidates = []
    for code, cdata in courses_data.items():
        topics = cdata["topics"]
        names = [t["name"] for t in topics]
        vecs = LocalEmbeddingService.encode_batch(names)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1e-10
        norm_vecs = vecs / norms
        sim_matrix = norm_vecs @ norm_vecs.T

        n = len(topics)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                sim = float(sim_matrix[i, j])
                if sim >= 0.45:
                    a_id = topics[i]["id"]
                    b_id = topics[j]["id"]
                    if is_valid_negative(code, a_id, b_id) and (code, a_id, b_id) not in selected_neg_keys:
                        high_sim_candidates.append((sim, code, a_id, b_id))

    high_sim_candidates.sort(key=lambda x: -x[0])
    high_sim_target = min(700, len(high_sim_candidates))
    for sim, code, a_id, b_id in high_sim_candidates[:high_sim_target]:
        selected_neg_keys.add((code, a_id, b_id))
        t_a = topic_map[code][a_id]
        t_b = topic_map[code][b_id]
        negative_rows.append({
            "course": code,
            "a_id": a_id,
            "b_id": b_id,
            "a_name": t_a["name"],
            "b_name": t_b["name"],
            "pos_a": t_a["position"],
            "pos_b": t_b["position"],
            "unit_a": t_a["module_idx"],
            "unit_b": t_b["module_idx"],
            "n_topics": courses_data[code]["n_topics"],
            "label": 0,
            "neg_type": "high_similarity_unlinked",
        })
    print(f"Generated {high_sim_target} high_similarity_unlinked negatives.")

    # Neg Type 4: random same-course pairs to reach target_neg_count exactly
    all_potential_random = []
    for code, cdata in courses_data.items():
        topics = cdata["topics"]
        n = len(topics)
        for i in range(n):
            for j in range(n):
                if i != j:
                    a_id = topics[i]["id"]
                    b_id = topics[j]["id"]
                    if is_valid_negative(code, a_id, b_id) and (code, a_id, b_id) not in selected_neg_keys:
                        all_potential_random.append((code, a_id, b_id))

    rng.shuffle(all_potential_random)
    needed = max(0, target_neg_count - len(negative_rows))
    for code, a_id, b_id in all_potential_random[:needed]:
        selected_neg_keys.add((code, a_id, b_id))
        t_a = topic_map[code][a_id]
        t_b = topic_map[code][b_id]
        negative_rows.append({
            "course": code,
            "a_id": a_id,
            "b_id": b_id,
            "a_name": t_a["name"],
            "b_name": t_b["name"],
            "pos_a": t_a["position"],
            "pos_b": t_b["position"],
            "unit_a": t_a["module_idx"],
            "unit_b": t_b["module_idx"],
            "n_topics": courses_data[code]["n_topics"],
            "label": 0,
            "neg_type": "random_same_course",
        })
    print(f"Generated {needed} random_same_course negatives.")
    print(f"Total negatives generated: {len(negative_rows)} (Target was {target_neg_count}).")


    # Combine and write CSV
    all_rows = positive_rows + negative_rows
    # Shuffle dataset with seed 42
    rng.shuffle(all_rows)

    out_csv = Path("DATA/processed/training_table_v5.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "course", "a_id", "b_id", "a_name", "b_name",
        "pos_a", "pos_b", "unit_a", "unit_b", "n_topics",
        "label", "neg_type"
    ]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_rows:
            writer.writerow(r)

    print("\n" + "=" * 60)
    print("TRAINING TABLE V5 SUMMARY")
    print("=" * 60)
    print(f"Output file: {out_csv}")
    print(f"Total rows: {len(all_rows)}")
    print(f"Positives: {len(positive_rows)}")
    print(f"Negatives: {len(negative_rows)} (ratio: {len(negative_rows)/len(positive_rows):.2f}:1)")
    from collections import Counter
    neg_counts = Counter(r["neg_type"] for r in negative_rows)
    for nt, cnt in neg_counts.items():
        print(f"  - {nt}: {cnt}")


if __name__ == "__main__":
    main()

