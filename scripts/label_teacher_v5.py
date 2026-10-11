import os
import sys
import json
import time
import random
import csv
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

load_dotenv()

from google import genai
from google.genai.errors import APIError


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY not found in environment or .env")
    return genai.Client(api_key=api_key)


def get_model_name():
    return os.getenv("GEMINI_MODEL") or os.getenv("EXTRACT_MODEL", "gemini-3.8-flash")


PROMPT_TEMPLATE = """You are an expert curriculum architect analyzing university computer science syllabi.
Course: {course_code} - {course_title}

Below is the list of topics taught in this course. Each topic has a unique ID (e.g. t1, t2).
{topic_list_text}

Task:
For EACH topic ID in the list, determine up to 3 DIRECT prerequisites chosen ONLY from this list by their ID.
A is a DIRECT prerequisite of B if:
1. Topic B strictly builds upon the core concepts of topic A.
2. A is an immediate foundational concept (do not include transitive prerequisites, e.g. if A->B->C, do not list A as prerequisite for C unless directly needed).
3. A precedes B in logical curriculum progression (an earlier topic in the syllabus). Do not assign later topics as prerequisites unless absolutely necessary.
4. No self-references: a topic cannot be its own prerequisite.
5. If a topic has NO direct prerequisite in this list (e.g. introductory topics or self-contained concepts), provide an empty list [].

Respond with a JSON object mapping each topic ID to a list of its direct prerequisite topic IDs:
{{
  "t1": [],
  "t2": ["t1"],
  ...
}}
Include EVERY topic ID from the provided list. Return JSON only.
"""


def format_topics(topics):
    return "\n".join(f"- [{t['id']}] {t['name']} (Module {t['module_idx']})" for t in topics)


def call_gemini_with_retry(client, model, prompt, max_retries=5):
    delay = 2.0
    current_model = model
    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model=current_model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.0,
                }
            )
            text = resp.text.strip()
            # Parse JSON
            data = json.loads(text)
            # Normalize if wrapped in a key
            if isinstance(data, dict):
                if "dependencies" in data and isinstance(data["dependencies"], dict):
                    data = data["dependencies"]
                elif "prerequisites" in data and isinstance(data["prerequisites"], dict):
                    data = data["prerequisites"]
                elif "topics" in data and isinstance(data["topics"], dict):
                    data = data["topics"]
                elif "dependencies" in data and isinstance(data["dependencies"], list):
                    data = {item.get("topic_id", item.get("id")): item.get("prerequisites", []) for item in data["dependencies"]}
            return data
        except Exception as e:
            err_str = str(e)
            print(f"  [Attempt {attempt+1}/{max_retries}] API error on {current_model}: {err_str}")
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                if current_model == "gemini-3.8-flash":
                    current_model = "gemini-3.5-flash-lite"
                    print(f"  Switching to fallback model: {current_model}")
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2.0
            else:
                raise


def parse_edges_from_response(raw_resp, topic_ids_set):
    """
    Given { "t2": ["t1"] }, return set of (a_id, b_id) where a is prerequisite of b.
    Enforce:
    - a_id in topic_ids_set, b_id in topic_ids_set
    - a_id != b_id
    - max 3 prerequisites per b_id
    """
    edges = set()
    if isinstance(raw_resp, dict):
        for b_id, prereqs in raw_resp.items():
            if b_id not in topic_ids_set:
                continue
            if not isinstance(prereqs, list):
                continue
            valid_prereqs = [a for a in prereqs if a in topic_ids_set and a != b_id]
            for a_id in valid_prereqs[:3]:
                edges.add((a_id, b_id))
    elif isinstance(raw_resp, list):
        for item in raw_resp:
            if isinstance(item, dict):
                b_id = item.get("topic_id") or item.get("id")
                prereqs = item.get("prerequisites") or item.get("direct_prerequisites", [])
                if b_id in topic_ids_set and isinstance(prereqs, list):
                    for a_id in [a for a in prereqs if a in topic_ids_set and a != b_id][:3]:
                        edges.add((a_id, b_id))
    return edges


def run_labeling():
    topics_file = Path("DATA/processed/topics_v5.json")
    assert topics_file.exists(), f"Missing {topics_file}"
    with open(topics_file, "r", encoding="utf-8") as f:
        courses_data = json.load(f)

    cache_dir = Path("DATA/processed/teacher_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    client = get_gemini_client()
    model = get_model_name()
    print(f"Using Gemini model: {model}")

    all_course_results = {}
    total_api_calls = 0

    for code, cdata in courses_data.items():
        title = cdata["course_title"]
        topics = cdata["topics"]
        topic_ids_set = {t["id"] for t in topics}
        name_map = {t["id"]: t["name"] for t in topics}

        print(f"\nProcessing course {code}: '{title}' ({len(topics)} topics)...")

        # Run 1: Original order
        cache_run1 = cache_dir / f"{code}_run1.json"
        if cache_run1.exists():
            print(f"  Run 1: Loaded from cache ({cache_run1})")
            with open(cache_run1, "r", encoding="utf-8") as f:
                resp1 = json.load(f)
        else:
            print("  Run 1: Calling Gemini (original order)...")
            prompt1 = PROMPT_TEMPLATE.format(
                course_code=code,
                course_title=title,
                topic_list_text=format_topics(topics)
            )
            resp1 = call_gemini_with_retry(client, model, prompt1)
            total_api_calls += 1
            with open(cache_run1, "w", encoding="utf-8") as f:
                json.dump(resp1, f, indent=2)
            time.sleep(1.0)

        # Run 2: Shuffled order (seed 42)
        cache_run2 = cache_dir / f"{code}_run2.json"
        if cache_run2.exists():
            print(f"  Run 2: Loaded from cache ({cache_run2})")
            with open(cache_run2, "r", encoding="utf-8") as f:
                resp2 = json.load(f)
        else:
            print("  Run 2: Calling Gemini (shuffled order, seed=42)...")
            shuffled_topics = list(topics)
            random.Random(42).shuffle(shuffled_topics)
            prompt2 = PROMPT_TEMPLATE.format(
                course_code=code,
                course_title=title,
                topic_list_text=format_topics(shuffled_topics)
            )
            resp2 = call_gemini_with_retry(client, model, prompt2)
            total_api_calls += 1
            with open(cache_run2, "w", encoding="utf-8") as f:
                json.dump(resp2, f, indent=2)
            time.sleep(1.0)

        edges1 = parse_edges_from_response(resp1, topic_ids_set)
        edges2 = parse_edges_from_response(resp2, topic_ids_set)

        confident_edges = edges1 & edges2
        all_edges = edges1 | edges2
        agreement = (len(confident_edges) / len(all_edges)) * 100 if all_edges else 100.0

        print(f"  Run 1 edges: {len(edges1)}, Run 2 edges: {len(edges2)}")
        print(f"  Confident (both runs): {len(confident_edges)}, Total union: {len(all_edges)}")
        print(f"  Agreement rate: {agreement:.1f}%")

        all_course_results[code] = {
            "name_map": name_map,
            "edges1": edges1,
            "edges2": edges2,
            "confident": confident_edges,
            "all_edges": all_edges,
            "agreement": agreement,
        }

    # Check for failing courses (<50% agreement) to tighten and rerun once
    failing_courses = [c for c, r in all_course_results.items() if r["agreement"] < 50.0]
    if failing_courses:
        print(f"\n[Tightening] Found {len(failing_courses)} course(s) with agreement < 50%: {failing_courses}")
        tightened_template = PROMPT_TEMPLATE.replace(
            "Task:",
            "Task (Strict & Conservative):\n"
            "BE HIGHLY SELECTIVE AND CONSERVATIVE. Only include A as prerequisite of B if understanding B is IMPOSSIBLE without A.\n"
            "Do NOT link topics merely because they share a domain or module. Most topics have 0 prerequisites, at most 1-2."
        )
        for code in failing_courses:
            print(f"  Rerunning failing course {code} with tightened prompt...")
            cdata = courses_data[code]
            title = cdata["course_title"]
            topics = cdata["topics"]
            topic_ids_set = {t["id"] for t in topics}

            # Run 1 tightened
            p1 = tightened_template.format(
                course_code=code, course_title=title, topic_list_text=format_topics(topics)
            )
            resp1 = call_gemini_with_retry(client, "gemini-3.5-flash-lite", p1)
            total_api_calls += 1
            cache_run1 = cache_dir / f"{code}_run1.json"
            with open(cache_run1, "w", encoding="utf-8") as f:
                json.dump(resp1, f, indent=2)
            time.sleep(1.0)

            # Run 2 tightened (shuffled)
            shuffled_topics = list(topics)
            random.Random(42).shuffle(shuffled_topics)
            p2 = tightened_template.format(
                course_code=code, course_title=title, topic_list_text=format_topics(shuffled_topics)
            )
            resp2 = call_gemini_with_retry(client, "gemini-3.5-flash-lite", p2)
            total_api_calls += 1
            cache_run2 = cache_dir / f"{code}_run2.json"
            with open(cache_run2, "w", encoding="utf-8") as f:
                json.dump(resp2, f, indent=2)
            time.sleep(1.0)

            edges1 = parse_edges_from_response(resp1, topic_ids_set)
            edges2 = parse_edges_from_response(resp2, topic_ids_set)
            confident_edges = edges1 & edges2
            all_edges = edges1 | edges2
            agr = (len(confident_edges) / len(all_edges) * 100) if all_edges else 100.0

            print(f"  Course {code} post-tightening: confident={len(confident_edges)}, union={len(all_edges)}, agreement={agr:.1f}%")
            all_course_results[code]["edges1"] = edges1
            all_course_results[code]["edges2"] = edges2
            all_course_results[code]["confident"] = confident_edges
            all_course_results[code]["all_edges"] = all_edges
            all_course_results[code]["agreement"] = agr

    # Write output CSV: DATA/processed/teacher_edges_v5.csv
    csv_path = Path("DATA/processed/teacher_edges_v5.csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    total_confident = 0
    total_uncertain = 0

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["course", "a_id", "b_id", "a_name", "b_name", "status"])
        for code, res in all_course_results.items():
            name_map = res["name_map"]
            for a_id, b_id in sorted(res["all_edges"]):
                status = "confident" if (a_id, b_id) in res["confident"] else "uncertain"
                if status == "confident":
                    total_confident += 1
                else:
                    total_uncertain += 1
                writer.writerow([
                    code,
                    a_id,
                    b_id,
                    name_map.get(a_id, a_id),
                    name_map.get(b_id, b_id),
                    status
                ])

    overall_union = total_confident + total_uncertain
    overall_agreement = (total_confident / overall_union * 100) if overall_union else 0.0

    print("\n" + "=" * 60)
    print("TEACHER LABELING SUMMARY (V5)")
    print("=" * 60)
    print(f"Total API calls made this run: {total_api_calls}")
    print(f"Total theory courses processed: {len(all_course_results)}")
    print(f"Total unique edges extracted: {overall_union}")
    print(f"Confident edges (in both runs): {total_confident}")
    print(f"Uncertain edges (in one run): {total_uncertain}")
    print(f"Overall agreement rate: {overall_agreement:.2f}%")
    print(f"Saved edges to: {csv_path}")

    for code, res in all_course_results.items():
        print(f"Course {code}: confident={len(res['confident'])}, uncertain={len(res['all_edges'] - res['confident'])}, agreement={res['agreement']:.1f}%")

    return total_api_calls, overall_agreement


if __name__ == "__main__":
    run_labeling()

