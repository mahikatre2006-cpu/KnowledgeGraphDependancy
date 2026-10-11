import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=== Searching for 8-60 or topic count limits in PLAN.md ===")
with open("PLAN.md", "r", encoding="utf-8") as f:
    for idx, line in enumerate(f, 1):
        if any(k in line.lower() for k in ["60", "8-60", "8 to 60", "topics extracted", "target", "granularity"]):
            print(f"PLAN.md:{idx}: {line.strip()}")

print("\n=== Searching for 8-60 in scripts/ ===")
import glob
for p in glob.glob("scripts/*.py"):
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        for idx, line in enumerate(f, 1):
            if "60" in line and "8" in line:
                print(f"{p}:{idx}: {line.strip()}")

