import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('C:/Users/Siddhesh/.gemini/antigravity/brain/e0f3173c-36fc-49a1-9025-0817dc096985/.system_generated/logs/transcript.jsonl', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f):
        data = json.loads(line)
        content = data.get('content', '')
        if isinstance(content, str) and ('78' in content or 'pilot' in content.lower()):
            for l in content.splitlines():
                if any(k in l.lower() for k in ['78', 'failure', 'threshold', '< 5%', '<5%', '<= 8', '<=8', '8 out of', 'decision rule']):
                    print(f"[Line {idx}] {l}")

