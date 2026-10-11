import fitz
import re

doc = fitz.open('tests/fixtures/nep_sem5_6.pdf')

def extract_page_blocks(page):
    blocks = [b for b in page.get_text('blocks') if b[6] == 0]
    blocks_sorted = sorted(blocks, key=lambda b: (b[1], b[0]))
    lines = []
    for b in blocks_sorted:
        for l in b[4].splitlines():
            if l.strip():
                lines.append(l.strip())
    return lines

mod_re = re.compile(r'^\s*([0-6])\s+(\S.*)')
self_learning_re = re.compile(r'Self[\s\-]*Learning\s+Topics?\s*:', re.I)
hours_co_re = re.compile(r'\s*\b\d{1,2}\s+(?:CO|LO)\d[\d,\s\-COLO]*$', re.I)

def split_outside_parens(text):
    parts = []
    depth = 0
    current = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == '(':
            depth += 1
            current.append(c)
        elif c == ')':
            depth = max(0, depth - 1)
            current.append(c)
        elif depth == 0:
            if c in (',', ';', ':'):
                parts.append(''.join(current))
                current = []
            elif c == ' ' and i + 2 < len(text) and text[i:i+3] in (' - ', ' – ', ' — '):
                parts.append(''.join(current))
                current = []
                i += 3
                continue
            else:
                current.append(c)
        else:
            current.append(c)
        i += 1
    if current:
        parts.append(''.join(current))
    return parts

results = {}

for pno, page in enumerate(doc):
    lines = extract_page_blocks(page)
    # check course code
    header_text = ' '.join(lines[:6])
    code_m = re.search(r'\b(234511\d[A-Z]?)\b', header_text)
    if not code_m:
        continue
    code = code_m.group(1)
    
    # 3. Title = join header lines until the "Teaching Scheme" line.
    # Kind = lab if the code is the lab code per the "Lab Description" table or the text contains "Lab Objectives".
    title_lines = []
    in_title = False
    for l in lines:
        if 'teaching scheme' in l.lower() or 'theory  practical' in l.lower():
            break
        # strip course code line
        if code in l:
            cleaned = l.replace(code, '').strip()
            cleaned = re.sub(r'Course\s+Code\s*\|\s*Course\s+Name\s*\|\s*Teaching\s+Scheme', '', cleaned, flags=re.I).strip()
            cleaned = cleaned.strip('|').strip()
            if cleaned:
                title_lines.append(cleaned)
            in_title = True
        elif in_title:
            cleaned = l.strip('|').strip()
            if cleaned:
                title_lines.append(cleaned)
    course_title = ' '.join(title_lines).strip()
    
    page_text = '\n'.join(lines)
    is_lab = ('lab objectives' in page_text.lower() or 'lab description' in page_text.lower() or code.endswith('L'))
    kind = 'lab' if is_lab else 'theory'

    # Detailed Syllabus to Total Hours
    ds_idx = -1
    th_idx = -1
    for i, l in enumerate(lines):
        if 'detailed syllabus' in l.lower() and ds_idx == -1:
            ds_idx = i
        if 'total hours' in l.lower() and th_idx == -1:
            th_idx = i
    
    if ds_idx == -1 or th_idx == -1:
        continue
        
    syllabus_lines = lines[ds_idx+1:th_idx]
    
    modules = []
    cur_num = None
    cur_title = None
    cur_lines = []

    def flush():
        if cur_num is not None:
            modules.append((cur_num, cur_title, cur_lines[:]))

    for line in syllabus_lines:
        m = mod_re.match(line)
        if m:
            flush()
            cur_num = int(m.group(1))
            cur_title = m.group(2).strip()
            cur_lines = []
        else:
            if cur_num is not None:
                cur_lines.append(line)
    flush()

    course_topics = []
    mod_counts = []
    for num, mtitle, clines in modules:
        if num == 0:
            continue
        content = ' '.join(clines)
        sl_m = self_learning_re.search(content)
        if sl_m:
            content = content[:sl_m.start()]
        content = hours_co_re.sub('', content).strip()
        parts = split_outside_parens(content)
        topics = [p.strip().strip('.,;:') for p in parts if p.strip()]
        mod_counts.append((num, mtitle, len(topics)))
        course_topics.extend(topics)
    
    results[code] = {
        'title': course_title,
        'kind': kind,
        'topics_count': len(course_topics),
        'modules': mod_counts
    }

for c in ['2345111', '2345112', '2345113']:
    info = results.get(c, {})
    print(f"Course {c}: {info.get('title')} ({info.get('kind')}) -> {info.get('topics_count')} topics")
    for m in info.get('modules', []):
        print(f"  Mod {m[0]}: {m[2]} topics ({m[1]})")
