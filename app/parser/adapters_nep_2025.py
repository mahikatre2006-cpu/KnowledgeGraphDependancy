"""
adapters_nep_2025.py
====================
Adapter for Mumbai University NEP 2025-26 Second Year (SE) syllabus.
Course codes: 7 digits (e.g. 2023112, 2163112, 2113111, 2343111, etc.).
"""
import re
from typing import List, Tuple
from app.parser.nep_parse_v2 import NEPModule, NEPCourse, _topics

_ROMAN_MAP = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
    'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
}


def parse_nep_2025_text(text: str) -> Tuple[bool, List[NEPCourse]]:
    """Parse NEP 2025 text into NEPCourse list."""
    # Remove DRAFT COPY watermark globally
    text_clean = re.sub(r'(?i)\bdraft\s+copy\b', '', text)
    lines = [l.strip() for l in text_clean.replace('\x0c', '\n').splitlines()]
    lines = [l for l in lines if l]

    # Filter page headers & noise
    lines = [
        l for l in lines
        if not re.fullmatch(r'University of Mumbai.*|AC:.*|Item No.*|Page\s*\d+', l, re.I)
    ]

    courses = []
    seen = set()

    for i, l in enumerate(lines):
        m_code = re.fullmatch(r'(\d{7})', l)
        if not m_code or i + 1 >= len(lines):
            continue

        code = m_code.group(1)
        next_i = next(
            (j for j in range(i + 1, len(lines)) if re.fullmatch(r'\d{7}', lines[j])),
            len(lines)
        )
        span = lines[i:next_i]

        ds_i = next(
            (k for k, s in enumerate(span) if re.search(r'detail(?:ed)?\s+syllabus|detailed\s+contents', s, re.I)),
            None
        )
        if ds_i is None or code in seen:
            continue

        # Extract title
        t_lines = []
        for k in range(i + 1, min(i + 6, next_i)):
            if re.fullmatch(r'\d{1,2}|Credits?|Teaching Scheme.*|Examination Scheme.*|Theory.*', lines[k], re.I):
                break
            t_lines.append(lines[k])
        title = ' '.join(t_lines).strip()
        kind = 'lab' if ('lab' in title.lower() or bool(re.search(r'\blab\b|mini project', title, re.I))) else 'theory'

        sub = span[ds_i:]
        # Find start of table: row with 'Sr. No.' or Roman I or '0 Prerequisite'
        start_tab = next(
            (k for k, s in enumerate(sub)
             if re.search(r'sr\.?\s*no\.?|prerequisite|\bmodule\b', s, re.I) or s.replace(' ', '') in _ROMAN_MAP),
            0
        )
        end_tab = next(
            (k for k in range(start_tab + 1, len(sub))
             if re.match(r'^(?:Text\s*Books?|Reference\s*Books?|Assessment|Total\s+Hours|Term\s+Work):?', sub[k], re.I)),
            len(sub)
        )
        table_lines = sub[start_tab:end_tab]

        blocks = []
        cur = None
        expected = 1

        for idx, line in enumerate(table_lines):
            norm_roman = line.replace(' ', '')
            is_mod = False

            if norm_roman in _ROMAN_MAP and _ROMAN_MAP[norm_roman] == expected:
                is_mod = True
            elif re.fullmatch(r'[1-6]', line) and int(line) == expected:
                if idx + 1 < len(table_lines):
                    nxt = table_lines[idx + 1]
                    if nxt.replace(' ', '') in _ROMAN_MAP and _ROMAN_MAP[nxt.replace(' ', '')] == expected:
                        continue
                    if not re.match(r'^(?:CO|LO|L0|\d)', nxt, re.I):
                        is_mod = True

            if is_mod:
                cur = [expected, []]
                blocks.append(cur)
                expected += 1
            elif cur is not None:
                cur[1].append(line)

        mods = []
        for m_num, m_lines in blocks:
            clean = [
                line for line in m_lines
                if not re.fullmatch(r'\d{1,2}|(?:CO|LO|L0)\s?\d(?:\s*[,\-–]\s*(?:CO|LO|L0)?\s?\d)*', line, re.I)
            ]
            if not clean:
                continue

            name_lines = [clean[0]]
            p = 1
            if p < len(clean):
                nxt = clean[p]
                if re.match(r'^(?:and|&|of|for|in)\b', nxt, re.I) or nxt[:1].islower():
                    name_lines.append(nxt)
                    p += 1
                elif p + 1 < len(clean) and ':' in clean[p + 1] and len(nxt.split()) <= 2:
                    name_lines.append(nxt)
                    p += 1

            m_name = ' '.join(name_lines).strip() or f"Module {m_num}"

            text_mod = ''
            for ml in clean[p:]:
                text_mod = text_mod + ml if (text_mod.endswith('-') and ml[:1].islower()) else text_mod + ' ' + ml

            # Cut from Self-Learning / Self-Study
            text_mod = re.split(r'self[\s-]*(?:learning|study)', text_mod, flags=re.I)[0]
            # Strip hour/CO tails e.g. "5 CO1" or "CO 1"
            text_mod = re.sub(r'\b\d{1,2}\s+(?:CO|LO|L0)\s?\d(?:\s*[,\-–]\s*(?:CO|LO|L0)?\s?\d)*\b', '', text_mod, flags=re.I)
            text_mod = re.sub(r'\b(?:CO|LO|L0)\s*\d\b', '', text_mod, flags=re.I)
            # Remove math item numbers like "1. 2. 3." or "1.1, 2.1"
            text_mod = re.sub(r'\b\d+\.\d+\b', '', text_mod)
            text_mod = re.sub(r'(?<=\s)\d+\.\s+', '', text_mod)

            tops = _topics(text_mod)
            mods.append(NEPModule(m_num, m_name, tops))

        if mods and any(m.topics for m in mods):
            seen.add(code)
            courses.append(NEPCourse(code, title, kind, mods))

    return bool(courses), courses

