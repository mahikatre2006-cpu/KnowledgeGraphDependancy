"""
adapters_rev2019_comps.py
=========================
Adapter for Mumbai University Computer Engineering REV-2019 ('C' Scheme) syllabus.
Course codes: CSC3xx/4xx (theory), CSL3xx/4xx (labs).
"""
import re
from typing import List, Tuple
from app.parser.nep_parse_v2 import NEPModule, NEPCourse, _topics


def parse_rev2019_comps_text(text: str) -> Tuple[bool, List[NEPCourse]]:
    """Parse Comps REV-2019 text into NEPCourse list."""
    lines = [l.strip() for l in text.replace('\x0c', '\n').splitlines()]
    lines = [l for l in lines if l]

    # Filter watermarks & page headers
    lines = [
        l for l in lines
        if not re.fullmatch(r'draft\s+copy', l, re.I)
        and not re.fullmatch(r'University of Mumbai.*|AC:.*|Item No.*|Page\s*\d+', l, re.I)
    ]

    courses = []
    seen = set()

    for i, l in enumerate(lines):
        m_code = re.fullmatch(r'(CSC\d{3}|CSL\d{3})', l)
        if not m_code or i + 1 >= len(lines):
            continue

        code = m_code.group(1)
        next_i = next(
            (j for j in range(i + 1, len(lines)) if re.fullmatch(r'(CSC\d{3}|CSL\d{3})', lines[j])),
            len(lines)
        )
        span = lines[i:next_i]

        is_theory = any(
            re.search(r'module\s+detailed\s+content|detailed\s+content|module\s+content', s, re.I)
            for s in span
        )
        is_lab = code.startswith('CSL') or any(
            re.search(r'suggested\s+experiments|experiment\s+list|lab\s+objectives', s, re.I)
            for s in span
        )

        if not is_theory and not is_lab:
            continue
        if code in seen:
            continue

        # Extract title
        t_lines = []
        for k in range(i + 1, min(i + 5, next_i)):
            if re.fullmatch(r'\d{1,2}|Credits?|Teaching Scheme.*|Examination Scheme.*', lines[k], re.I):
                break
            t_lines.append(lines[k])
        title = ' '.join(t_lines).strip()
        kind = 'lab' if (code.startswith('CSL') or 'lab' in title.lower()) else 'theory'

        if is_theory:
            th_i = next(
                (k for k, s in enumerate(span) if re.search(r'detailed\s+content|module\s+content', s, re.I)),
                None
            )
            if th_i is None:
                continue

            end_k = next(
                (k for k in range(th_i + 1, len(span))
                 if re.match(r'^(?:Textbooks?|Text\s+Books?|References?|Assessment|Useful\s+Links):?', span[k], re.I)),
                len(span)
            )
            table_lines = span[th_i:end_k]

            blocks = []
            cur = None
            expected = 1
            for idx, line in enumerate(table_lines):
                # Check for module start: '1', '2', etc. followed by title line
                if line == str(expected) and idx + 1 < len(table_lines) and not table_lines[idx + 1][:1].isdigit():
                    cur = [expected, table_lines[idx + 1], []]
                    blocks.append(cur)
                    expected += 1
                elif cur is not None:
                    # Skip module title line and immediate hours line
                    if line == cur[1]:
                        continue
                    if len(cur[2]) == 0 and line.isdigit():
                        continue
                    cur[2].append(line)

            mods = []
            for m_num, m_name, m_lines in blocks:
                # Join lines with hyphen handling
                text_mod = ''
                for ml in m_lines:
                    text_mod = text_mod + ml if (text_mod.endswith('-') and ml[:1].islower()) else text_mod + ' ' + ml
                # Cut from Self-Learning / Self-Study
                text_mod = re.split(r'self[\s-]*(?:learning|study)', text_mod, flags=re.I)[0]
                # Strip hour/CO tails
                text_mod = re.sub(r'\b\d{1,2}\s+(?:CO|LO|L0)\s?\d(?:\s*[,\-–]\s*(?:CO|LO|L0)?\s?\d)*\b', '', text_mod, flags=re.I)
                # Strip sub-item numbers like 1.1, 2.1
                text_mod = re.sub(r'\b\d+\.\d+\b', '', text_mod)
                # Filter topics
                tops = _topics(text_mod)
                mods.append(NEPModule(m_num, m_name or f"Module {m_num}", tops))

            if mods and any(m.topics for m in mods):
                seen.add(code)
                courses.append(NEPCourse(code, title, kind, mods))

        elif is_lab:
            exp_i = next(
                (k for k, s in enumerate(span) if re.search(r'name\s+of\s+the\s+experiment|suggested\s+experiments|experiment\s+list', s, re.I)),
                None
            )
            if exp_i is None:
                continue

            end_k = next(
                (k for k in range(exp_i + 1, len(span))
                 if re.match(r'^(?:Useful\s+Links|Term\s+Work|Textbooks?|References?):?', span[k], re.I)),
                len(span)
            )
            exp_lines = span[exp_i:end_k]

            exps = []
            for el in exp_lines:
                m_exp = re.match(r'^\d+\*?\s*(.+)', el)
                if m_exp:
                    exps.append(m_exp.group(1))
                elif exps and not re.match(r'^(?:Sr\.?\s*No\.?|Name|Hours|Module)', el, re.I):
                    exps[-1] = exps[-1] + ' ' + el

            lab_topics = []
            for exp in exps:
                clean_exp = re.split(r'self[\s-]*(?:learning|study)', exp, flags=re.I)[0]
                clean_exp = re.sub(r'\b\d{1,2}\s+(?:CO|LO|L0)\s?\d.*', '', clean_exp, flags=re.I)
                lab_topics.extend(_topics(clean_exp))

            if lab_topics:
                seen.add(code)
                courses.append(NEPCourse(code, title, 'lab', [NEPModule(1, 'Lab Experiments', lab_topics)]))

    return bool(courses), courses

