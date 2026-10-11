import os

for root, dirs, files in os.walk('.'):
    if 'venv' in root or '.git' in root:
        continue
    for file in files:
        if file.endswith('.py') or file.endswith('.md') or file.endswith('.txt'):
            p = os.path.join(root, file)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if 'decision rule' in content.lower() or 'pilot gate' in content.lower() or 'gate check' in content.lower():
                        print(f"Found match in {p}")
                        for line in content.splitlines():
                            if any(k in line.lower() for k in ['decision rule', 'pilot gate', 'rejection rate', '< 5% rejected', 'pilot decision']):
                                print(f"  {line[:120]}")
            except Exception as e:
                pass

