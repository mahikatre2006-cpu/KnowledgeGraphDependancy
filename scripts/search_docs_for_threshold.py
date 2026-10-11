import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

for fname in ['DATA-pdf.md', 'README.md', 'PLAN.md', 'Gemini.md', 'audit_report.md']:
    if os.path.exists(fname):
        with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
            c = f.read()
            if '8' in c or '78' in c or 'threshold' in c:
                for line in c.splitlines():
                    if any(k in line.lower() for k in ['pilot', '78', 'failure', 'threshold', '<5%', '< 5%', '<= 8', '<=8', 'gate']):
                        print(f"{fname}: {line.strip()[:120]}")

