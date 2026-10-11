import sys
sys.stdout.reconfigure(encoding='utf-8')

from detailed_suspect_analysis import suspects

print("=== PROBABLE OVER-SPLITS ===")
for s in suspects:
    if s['classification'] == 'probable over-split':
        print(f"[{s['course']}] [{s['module']}] '{s['topic']}' | Quote: '{s['quote']}'")
        print(f"  Reason: {s['reason']}\n")

print("\n=== UNCERTAIN CASES ===")
for s in suspects:
    if s['classification'] == 'uncertain':
        print(f"[{s['course']}] [{s['module']}] '{s['topic']}' | Quote: '{s['quote']}'")
        print(f"  Reason: {s['reason']}\n")

