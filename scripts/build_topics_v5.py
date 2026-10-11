import os
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.parser.nep_parse_v2 import parse_nep_pdf_bytes


def main():
    pdf_path = Path("tests/fixtures/REAL_nep.pdf")
    if not pdf_path.exists():
        pdf_path = Path("tests/fixtures/nep_sem5_6.pdf")
    assert pdf_path.exists(), f"PDF fixture not found at {pdf_path}"

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    ok, courses, elapsed = parse_nep_pdf_bytes(pdf_bytes)
    assert ok, "Failed to parse syllabus PDF"

    # Filter theory courses only
    theory_courses = [c for c in courses if c.kind == "theory"]
    print(f"Extracted {len(courses)} courses total; {len(theory_courses)} theory courses.")

    output_data = {}
    print("\n--- Per-Course Topic Counts ---")
    total_topics = 0
    for c in theory_courses:
        course_topics = []
        topic_idx = 1
        for mod in c.modules:
            for t_name in mod.topics:
                course_topics.append({
                    "id": f"t{topic_idx}",
                    "name": t_name,
                    "module_idx": mod.index,
                    "position": topic_idx,
                })
                topic_idx += 1

        output_data[c.code] = {
            "course_code": c.code,
            "course_title": c.title,
            "kind": c.kind,
            "n_topics": len(course_topics),
            "modules": [
                {
                    "index": m.index,
                    "name": m.name,
                    "topics": m.topics,
                }
                for m in c.modules
            ],
            "topics": course_topics,
        }
        total_topics += len(course_topics)
        print(f"Course {c.code} ({c.title}): {len(course_topics)} topics across {len(c.modules)} modules")

    print(f"\nTotal theory courses: {len(theory_courses)}")
    print(f"Total topics: {total_topics}")

    out_path = Path("DATA/processed/topics_v5.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(output_data)} theory courses to {out_path}")


if __name__ == "__main__":
    main()
