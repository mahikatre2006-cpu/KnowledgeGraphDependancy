import os
import re

for root, dirs, files in os.walk('.'):
    if 'venv' in root or '.git' in root or 'node_modules' in root: continue
    for file in files:
        p = os.path.join(root, file)
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                c = f.read()
                # look for 8 failures or 8 out of 78 or <= 8 or <=8
                matches = re.findall(r'.{0,50}(?:[<≤=]\s*8|8\s*(?:out of|/)\s*78|8\s*failures|10%|rejection).{0,50}', c, re.IGNORECASE)
                if matches:
                    for m in matches[:3]:
                        if any(k in m.lower() for k in ['78', 'failure', 'pilot', 'gate', 'rejection', '<5%']):
                            print(f"{p}: {m.strip()}")
        except Exception:
            pass

