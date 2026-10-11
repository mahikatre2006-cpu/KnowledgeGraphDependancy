"""
adapters_rev2019_it.py
======================
Adapter for Mumbai University Information Technology REV-2019 ('C' Scheme) syllabus.
Course codes: ITC3xx/4xx/5xx/6xx/7xx/8xx (theory), ITL3xx/4xx/5xx/6xx/7xx/8xx (labs).
"""
import re
from typing import List, Tuple
from app.parser.nep_parse_v2 import NEPModule, NEPCourse, _topics

_ROMAN_MAP = {
    'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6,
    'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10
}


def parse_rev2019_it_text(text: str) -> Tuple[bool, List[NEPCourse]]:
    """Parse IT REV-2019 text into NEPCourse list."""
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
        m_code = re.fullmatch(r'(ITC\d{3}|ITL\d{3})', l)
        if not m_code or i + 1 >= len(lines):
            continue

        code = m_code.group(1)
        next_i = next(
            (j for j in range(i + 1, len(lines)) if re.fullmatch(r'(ITC\d{3}|ITL\d{3})', lines[j])),
            len(lines)
        )
        span = lines[i:next_i]

        ds_i = next(
            (k for k, s in enumerate(span) if re.search(r'detailed\s+syllabus', s, re.I)),
            None
        )
        if ds_i is None or code in seen:
            continue

        # Extract title
        t_lines = []
        for k in range(i + 1, min(i + 5, next_i)):
            if re.fullmatch(r'\d{1,2}|Credits?|Teaching Scheme.*|Examination Scheme.*', lines[k], re.I):
                break
            t_lines.append(lines[k])
        title = ' '.join(t_lines).strip()
        kind = 'lab' if (code.startswith('ITL') or 'lab' in title.lower()) else 'theory'

        # Module table runs from DETAILED SYLLABUS until end markers
        # End markers: Textbooks / References / Assessment (when appearing after table starts)
        sub = span[ds_i:]
        # Find start of table: row with 'Sr. No.' or Roman I or '0 Prerequisite'
        start_tab = next(
            (k for k, s in enumerate(sub)
             if re.search(r'sr\.?\s*no\.?|prerequisite|\bmodule\b', s, re.I) or s.replace(' ', '') in _ROMAN_MAP),
            0
        )
        # Find end after table starts
        end_tab = next(
            (k for k in range(start_tab + 1, len(sub))
             if re.match(r'^(?:Textbooks?|Text\s+Books?|References?|Assessment|Useful\s+Links|Term\s+Work\s+Marks):?', sub[k], re.I)),
            len(sub)
        )
        table_lines = sub[start_tab:end_tab]

        # Scan module blocks
        blocks = []
        cur = None
        expected = 1

        idx = 0
        while idx < len(table_lines):
            line = table_lines[idx]

            # Normalize potential spaced Roman numerals like "I I I" -> "III"
            norm_roman = line.replace(' ', '')

            # Check math format: "01 Module: Laplace Transform"
            m_math = re.match(r'^0?(\d+)\s*Module\s*:\s*(.*)', line, re.I)

            is_mod = False
            mod_title = None

            if m_math and int(m_math.group(1)) == expected:
                is_mod = True
                mod_title = m_math.group(2).strip()
            elif norm_roman in _ROMAN_MAP and _ROMAN_MAP[norm_roman] == expected:
                is_mod = True
            elif re.fullmatch(r'[1-6]', line) and int(line) == expected:
                is_mod = True

            if is_mod:
                cur = [expected, mod_title, []]
                blocks.append(cur)
                expected += 1
            elif cur is not None:
                # Exclude row 0 Prerequisite
                cur[2].append(line)
            idx += 1

        mods = []
        for m_num, m_name, m_lines in blocks:
            # Strip noise and CO/hour lines
            clean = [
                line for line in m_lines
                if not re.fullmatch(r'\d{1,2}|(?:CO|LO|L0)\s?\d(?:\s*[,\-–]\s*(?:CO|LO|L0)?\s?\d)*', line, re.I)
            ]
            if not m_name:
                name_lines = []
                p = 0
                while p < len(clean) and len(name_lines) < 3 and not re.search(r'[,;]', clean[p]):
                    name_lines.append(clean[p].rstrip(':'))
                    p += 1
                m_name = ' '.join(name_lines).strip() or f"Module {m_num}"
                content_lines = clean[p:]
            else:
                content_lines = clean

            text_mod = ''
            for ml in content_lines:
                text_mod = text_mod + ml if (text_mod.endswith('-') and ml[:1].islower()) else text_mod + ' ' + ml

            # Cut from Self-Learning / Self-Study
            text_mod = re.split(r'self[\s-]*(?:learning|study)', text_mod, flags=re.I)[0]
            # Strip hour/CO tails
            text_mod = re.sub(r'\b\d{1,2}\s+(?:CO|LO|L0)\s?\d(?:\s*[,\-–]\s*(?:CO|LO|L0)?\s?\d)*\b', '', text_mod, flags=re.I)
            # Strip sub-item numbers e.g. 1.1, 2.1
            text_mod = re.sub(r'\b\d+\.\d+\b', '', text_mod)

            tops = _topics(text_mod)
            mods.append(NEPModule(m_num, m_name, tops))

        if mods and any(m.topics for m in mods):
            seen.add(code)
            courses.append(NEPCourse(code, title, kind, mods))

    return bool(courses), courses

