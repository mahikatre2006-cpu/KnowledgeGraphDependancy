import re, time
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class NEPModule:
    index: int
    name: str
    topics: List[str] = field(default_factory=list)


@dataclass
class NEPCourse:
    code: str
    title: str
    kind: str
    modules: List[NEPModule] = field(default_factory=list)

    @property
    def topics(self):
        return [(t, m.index) for m in self.modules for t in m.topics]

    @property
    def n_topics(self):
        return sum(len(m.topics) for m in self.modules)


_MARKERS = ["detailed syllabus", "course objectives", "course outcomes",
            "name of module", "self-learning topics", "course code"]
_SELF_RE = re.compile(r'self[\s-]*(?:learning|study)', re.I)
_NOISE = re.compile(r'\d{1,2}|(?:CO|LO|L0)\s?\d(?:\s*[,\-–]\s*(?:CO|LO|L0)?\s?\d)*', re.I)

_GENERIC = {"introduction", "overview", "basics", "best practices", "applications",
            "challenges", "case studies", "case study", "definition", "advantages",
            "disadvantages", "summary", "conclusion", "review", "general", "types",
            "concepts", "none", "practical", "theory", "contents", "content", "tools",
            "examples", "example", "fundamentals", "prerequisites", "prerequisite"}
_PROC = re.compile(r'^(installation|installing\b.*|environment setup|first app|'
                   r'folder (and|&) file structure|file structure|folder structure|'
                   r'set ?up\b.*|getting started)$', re.I)
_CAL = re.compile(r'\b(jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d|'
                  r'\b(mon|tues|wednes|thurs|fri|satur|sun)day\b|\b(holiday|break|vacation)\b|'
                  r'unit test|carried|all subjects|\bmod\.?\s*\d|^\d+\s*[-–]\s*\d+$', re.I)


def is_syllabus(text: str) -> bool:
    low = text.lower()
    return sum(1 for m in _MARKERS if m in low) >= 2


def _split_topics(text: str) -> List[str]:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'-\s+(?=[a-z])', '-', text)
    out, buf, depth, n = [], [], 0, len(text)
    for i, ch in enumerate(text):
        prev = text[i - 1] if i else ' '
        nxt = text[i + 1] if i + 1 < n else ' '
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth = max(0, depth - 1)
        sep = False
        if depth == 0:
            if ch in ',;:•–—|':
                sep = True
            elif ch == '-' and nxt == ' ' and (prev == ' ' or prev.isalnum()):
                sep = True
            elif ch == '.' and nxt == ' ' and i + 2 < n and text[i + 2].isupper():
                sep = True
        if sep:
            out.append(''.join(buf)); buf = []
        else:
            buf.append(ch)
    out.append(''.join(buf))
    return out


def _valid(t: str) -> bool:
    w = t.split()
    if not (1 <= len(w) <= 10) or len(t) < 2 or not re.search(r'[A-Za-z]', t):
        return False
    l = t.lower()
    return not (l in _GENERIC or _PROC.match(t) or _CAL.search(l)
                or re.match(r'^(unit|module)\b', l))


def _topics(content: str) -> List[str]:
    res = []
    for p in _split_topics(content):
        t = p.strip(' .;:,-–—•"\'\t')
        t = re.sub(r'^(?:and|including|such as|like|etc)\s+', '', t, flags=re.I)
        t = re.sub(r'\s+etc\.?$', '', t, flags=re.I).strip(' .;:,-')
        if _valid(t):
            res.append(t)
    return res


def _find_header(lines, ds):
    for i in range(ds - 1, max(-1, ds - 400), -1):
        if re.fullmatch(r'23\d{5,6}', lines[i]):
            t = []
            for l in lines[i + 1:i + 7]:
                if re.fullmatch(r'[\d\-–—]+', l) or l[:1].isdigit():
                    break
                t.append(l)
            title = re.sub(r'\s+', ' ', " ".join(t)).strip()
            mid = " ".join(lines[i:ds]).lower()
            lab = 'lab objectives' in mid or bool(re.search(r'\blab\b|mini project', title, re.I))
            return lines[i], title, lab
    return None


def _parse_span(span):
    k = next((i for i, l in enumerate(span) if l == '0'), None)
    if k is None:
        return []
    blocks, cur, expected = [], None, 1
    for l in span[k + 1:]:
        if re.fullmatch(r'[1-6]', l) and int(l) == expected:
            cur = [expected, []]; blocks.append(cur); expected += 1
        elif cur is not None:
            cur[1].append(l)
    mods, seen = [], set()
    for n, raw in blocks:
        lines = [l for l in raw if not _NOISE.fullmatch(l) and l not in ('-', '--', '---')]
        name, i = [], 0
        while (i < len(lines) and len(name) < 4
               and not re.search(r'[,;:.]', lines[i]) and not _SELF_RE.search(lines[i])):
            name.append(lines[i]); i += 1
        text = ""
        for l in lines[i:]:
            text = text + l if (text.endswith('-') and l[:1].islower()) else text + ' ' + l
        text = _SELF_RE.split(text)[0]
        text = re.split(r'\bPractical\s*:', text)[0]
        text = re.sub(r'^\s*Contents?\s*:\s*', '', text.strip())
        tops = []
        for t in _topics(text):
            key = t.lower()
            if key not in seen:
                seen.add(key); tops.append(t)
        mods.append(NEPModule(n, re.sub(r'\s+', ' ', " ".join(name)).strip() or f"Module {n}", tops))
    return mods


def parse_nep_text(text):
    lines = [l.strip() for l in text.replace('\x0c', '\n').splitlines()]
    lines = [l for l in lines if l]
    courses, done = [], set()
    for i, l in enumerate(lines):
        if not l.lower().startswith('detailed syllabus'):
            continue
        h = _find_header(lines, i)
        if not h or h[0] in done:
            continue
        end = next((j for j in range(i + 1, len(lines)) if re.match(r'^Total\b', lines[j])), len(lines))
        mods = _parse_span(lines[i + 1:end])
        if not any(m.topics for m in mods):
            continue
        done.add(h[0])
        courses.append(NEPCourse(h[0], h[1], "lab" if h[2] else "theory", mods))
    return bool(courses), courses


def parse_nep_pdf_bytes(pdf_bytes: bytes):
    import fitz
    t0 = time.perf_counter()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(p.get_text() for p in doc)
    if not is_syllabus(text):
        return False, [], time.perf_counter() - t0
    ok, courses = parse_nep_text(text)
    return ok, courses, time.perf_counter() - t0