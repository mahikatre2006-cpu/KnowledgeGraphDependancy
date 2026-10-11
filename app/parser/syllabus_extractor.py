import re
from typing import List, Tuple
from app.models.parser_schemas import ParsedSyllabus, ParsedUnit, ParsedTopic


def slugify(text: str) -> str:
    """Converts a string into a clean ID slug (e.g. 'Linear Algebra 101' -> 'linear_algebra_101')."""
    slug = text.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    return slug.strip('_')


class SyllabusExtractor:
    """
    Parses cleaned syllabus text into structured Units and Topics.
    Uses robust regex patterns and noise filters to eliminate syllabus metadata,
    watermarks, grading schemes, and bibliographic citations.
    """

    # Regex patterns for unit / module header detection
    UNIT_HEADER_REGEX = re.compile(
        r'^(?:unit|module|chapter|part|section)\s*[-:]?\s*([0-9ivxlcdm]+|\w+)\s*[-:]?\s*(.*)$',
        re.IGNORECASE
    )

    COURSE_CODE_REGEX = re.compile(r'\b(\d{7}|[A-Z]{2,4}\s*[-:]?\s*\d{3,4})\b', re.IGNORECASE)

    # Core noise patterns ported from offline pipeline and live regression cases
    _NOISE_PATS = [
        # Observed junk strings & watermarks
        re.compile(r'\bTHIS\s+IS\s+A\s+STUDENT\b', re.IGNORECASE),
        re.compile(r'\bOFFICIAL\s+UNIVERSITY\b', re.IGNORECASE),
        re.compile(r'\bPREPARED\s+FOR\s+STUDY\s+AND\s+SYLLABUS\b', re.IGNORECASE),
        re.compile(r'\bDEMO\s*(?:/|\s*)\s*REFERENCE\s*COPY\b', re.IGNORECASE),
        re.compile(r'^\s*PAGE\s*\d+\s*$', re.IGNORECASE),
        re.compile(r'\bPAGE\s*\d+\b', re.IGNORECASE),
        re.compile(r'\bstudent(?:s)?\s+(?:shall|must|copy|guide|study)\b', re.IGNORECASE),
        re.compile(r'\b(university|mumbai)\s+of\s+mumbai\b', re.IGNORECASE),
        re.compile(r'^\s*rev\s*\d{4}\s*(?:scheme)?', re.IGNORECASE),
        re.compile(r'\bprepared\s+for\s+study\b', re.IGNORECASE),
        re.compile(r'\bdemo\s+copy\b', re.IGNORECASE),
        re.compile(r'\breference\s+copy\b', re.IGNORECASE),

        # Bare numbers and course codes
        re.compile(r'^\d{7}$'),
        re.compile(r'^[A-Z]{2,4}\d{3,4}$'),
        re.compile(r'^\d+$'),
        re.compile(r'^[-\u2013\u2014\s]+$'),
        re.compile(r'^(total|na|nil|n\.a\.|--|---)$', re.IGNORECASE),
        re.compile(r'^(unit|module|chapter|section|sr\.?\s*no\.?)$', re.IGNORECASE),
        re.compile(r'^(theory|practical|tutorial|credits?|marks?|hours?|hrs?)$', re.IGNORECASE),
        re.compile(r'^co\s*mapping', re.IGNORECASE),
        re.compile(r'^co\s*\d', re.IGNORECASE),
        re.compile(r'^\d{1,2}\s*[-\.]\s*$'),
        re.compile(r'^(https?|www\.)', re.IGNORECASE),
        re.compile(r'https?://', re.IGNORECASE),
        re.compile(r'^(reference|textbook|online|books?):?$', re.IGNORECASE),
        re.compile(r'^(iat|iat-i|iat-ii|end\s*sem|test\s*\d)$', re.IGNORECASE),
        re.compile(r'^prerequisite[s:]?$', re.IGNORECASE),
        re.compile(r'^rationale:?$', re.IGNORECASE),
        re.compile(r'^course\s*(objective|outcome|code|name|description)s?:?$', re.IGNORECASE),
        re.compile(r'^\s*(and|or|the|to|of|in|for|a|an)\s*$', re.IGNORECASE),
        re.compile(r'^self[\s-]learning\s*topics?:?\s*$', re.IGNORECASE),
        re.compile(r'^assessment:?$', re.IGNORECASE),
        re.compile(r'^(lab|mini\s*project|open\s*elective)', re.IGNORECASE),
        re.compile(r'^below\s+[\d.]+', re.IGNORECASE),
        re.compile(r'iat-i\s*\+\s*iat', re.IGNORECASE),
        re.compile(r'^course\s*code\s*course\s*name', re.IGNORECASE),
        re.compile(r'end\s*sem\s*exam', re.IGNORECASE),
        re.compile(r'teaching\s*scheme\s*\(contact\s*hours\)', re.IGNORECASE),
        re.compile(r'^\(average\)$', re.IGNORECASE),
        re.compile(r'^(explore|topics|concepts|overview|details)$', re.IGNORECASE),
        re.compile(r'^self-learning$', re.IGNORECASE),
        re.compile(r'^\(without\s*proof\)$', re.IGNORECASE),

        # Textbook & Bibliographic citations
        re.compile(r'^text\s*books?(\s*(and\s*)?references?)?:?\s*$', re.IGNORECASE),
        re.compile(r'^online\s+references?:?\s*$', re.IGNORECASE),
        re.compile(r'^(books?\s*)?references?:?\s*$', re.IGNORECASE),
        re.compile(r'^suggested\s+(list|reading)', re.IGNORECASE),
        re.compile(r'\b(edition|publication|press|publisher|vol\.|ISBN|reprint)\b', re.IGNORECASE),
        re.compile(r'\b(McGraw[\s\-]?Hill|Pearson|Wiley|PHI|BPB|Springer|Oxford|Cambridge|'
                   r'Tata\s*McGraw|Khanna|Narosa|Prentice[\s\-]?Hall|PACKT|Cengage|'
                   r'Elsevier|CRC\s*Press|Addison[\s\-]?Wesley|O\'Reilly|Manning)\b', re.IGNORECASE),
        re.compile(r'\bby\s+[A-Z][a-z]+(\s+[A-Z]\.?)?\s+[A-Z][a-z]+', re.IGNORECASE),

        # Exam / Assessment scheme bleed-in
        re.compile(r'internal\s+assessment', re.IGNORECASE),
        re.compile(r'question\s+paper\s+(format|will|comprise)', re.IGNORECASE),
        re.compile(r'term\s+work\s+(shall|marks|consists?)', re.IGNORECASE),
        re.compile(r'\bIA\s+will\s+consist', re.IGNORECASE),
        re.compile(r'compulsory\s+internal\s+assessment', re.IGNORECASE),
        re.compile(r'syllabus\s+content\s+must\s+be\s+covered', re.IGNORECASE),
        re.compile(r'oral\s+exam\s+will\s+be\s+held', re.IGNORECASE),

        # Guidelines & Self-learning preambles
        re.compile(r'faculty\s+(supervisor|guide)', re.IGNORECASE),
        re.compile(r'capstone\s+(mini|project)', re.IGNORECASE),
        re.compile(r'log\s*book\s+to\s+be\s+prepared', re.IGNORECASE),
        re.compile(r'(assessment|evaluation)\s+criteria\s+of', re.IGNORECASE),
        re.compile(r'guidelines\s+for\s+(labs?|assessment|capstone|conducting)', re.IGNORECASE),
        re.compile(r'two\s+reviews\s+will\s+be\s+conducted', re.IGNORECASE),
        re.compile(r'\b\w+\.(org|com|edu|net|gov)/\S*'),
        re.compile(r'^(self[\s-]?learning|learning)\s+topics?:', re.IGNORECASE),
        re.compile(r'^learning\s+topics?:', re.IGNORECASE),
        re.compile(r'^note:\s*no\s+questions', re.IGNORECASE),
        re.compile(r'students\s+are\s+encouraged\s+to\s+explore', re.IGNORECASE),
        re.compile(r'\b(letter\s+grades?|grade\s+points?|semester\s+gpa|cgpa|faculty\s+of)\b', re.IGNORECASE),
        re.compile(r'\b(note\s+for\s+qp|qp\s+setters?|question\s+paper\s+should)\b', re.IGNORECASE),
        re.compile(r'\b(date\s+of\s+exam|duration:\s*\d+|max\.?\s*marks)\b', re.IGNORECASE),
        re.compile(r'\b(question\s+\d+\s+is\s+compulsory|remaining\s+questions)\b', re.IGNORECASE),
        re.compile(r'\b(all\s+cos\s+should\s+be\s+mapped|module\s+weightage)\b', re.IGNORECASE),
        re.compile(r'\b(NPTEL|W3Schools?|Coursera|edX|GeeksforGeeks|TutorialsPoint)\b', re.IGNORECASE),
    ]

    @classmethod
    def parse_multi(cls, text: str) -> List[ParsedSyllabus]:
        """Splits text into multiple subjects based on course code boundaries."""
        if not text or not text.strip():
            return []

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        subject_blocks = []
        current_block = []

        for line in lines:
            if cls.COURSE_CODE_REGEX.search(line):
                if current_block:
                    subject_blocks.append(current_block)
                current_block = [line]
            else:
                current_block.append(line)

        if current_block:
            subject_blocks.append(current_block)

        results = []
        for block_lines in subject_blocks:
            block_text = "\n".join(block_lines)

            course_code = cls._extract_course_code(block_text)
            course_title = cls._extract_course_title(block_lines)

            unit_blocks = cls._segment_into_units(block_lines)

            parsed_units = []
            all_topics = []
            unit_counter = 1

            for unit_header, blines in unit_blocks:
                unit_topics = cls._extract_topics_from_block(blines, unit_counter, unit_header)
                if unit_topics:
                    parsed_units.append(ParsedUnit(unit_number=unit_counter, title=unit_header, topics=unit_topics))
                    all_topics.extend(unit_topics)
                    unit_counter += 1

            if not parsed_units and block_lines:
                fallback = cls._extract_topics_from_block(block_lines, 1, "General Syllabus Topics")
                if fallback:
                    parsed_units.append(ParsedUnit(unit_number=1, title="General Syllabus Topics", topics=fallback))
                    all_topics.extend(fallback)

            if all_topics:
                results.append(ParsedSyllabus(
                    course_title=course_title,
                    course_code=course_code,
                    units=parsed_units,
                    all_topics=all_topics,
                    total_topics_count=len(all_topics)
                ))

        return results

    @classmethod
    def parse(cls, text: str) -> ParsedSyllabus:
        """Parses raw text content of a syllabus into a structured ParsedSyllabus object."""
        if not text or not text.strip():
            return ParsedSyllabus(
                course_title="Empty Syllabus",
                course_code="",
                units=[],
                all_topics=[],
                total_topics_count=0
            )

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        course_code = cls._extract_course_code(text)
        course_title = cls._extract_course_title(lines)

        unit_blocks = cls._segment_into_units(lines)

        parsed_units: List[ParsedUnit] = []
        all_topics: List[ParsedTopic] = []

        unit_counter = 1
        for unit_header, block_lines in unit_blocks:
            unit_topics = cls._extract_topics_from_block(block_lines, unit_counter, unit_header)

            if unit_topics:
                parsed_unit = ParsedUnit(
                    unit_number=unit_counter,
                    title=unit_header,
                    topics=unit_topics
                )
                parsed_units.append(parsed_unit)
                all_topics.extend(unit_topics)
                unit_counter += 1

        if not parsed_units and lines:
            fallback_topics = cls._extract_topics_from_block(lines, unit_number=1, unit_title="General Syllabus Topics")
            if fallback_topics:
                parsed_unit = ParsedUnit(
                    unit_number=1,
                    title="General Syllabus Topics",
                    topics=fallback_topics
                )
                parsed_units.append(parsed_unit)
                all_topics.extend(fallback_topics)

        return ParsedSyllabus(
            course_title=course_title,
            course_code=course_code,
            units=parsed_units,
            all_topics=all_topics,
            total_topics_count=len(all_topics)
        )

    @classmethod
    def _extract_course_code(cls, text: str) -> str:
        match = cls.COURSE_CODE_REGEX.search(text)
        return match.group(1).upper() if match else ""

    @classmethod
    def _extract_course_title(cls, lines: List[str]) -> str:
        for line in lines[:5]:
            if not cls.UNIT_HEADER_REGEX.match(line) and 3 < len(line) < 80:
                clean = re.sub(r'^[A-Z]{2,4}\s*[-:]?\s*\d{3,4}\s*[:|-]?\s*', '', line, flags=re.IGNORECASE)
                clean = re.sub(r'^(course|syllabus|subject)\s*[:|-]\s*', '', clean, flags=re.IGNORECASE)
                clean = clean.strip()
                if not cls._is_noise(clean):
                    return clean
        return "Course Syllabus"

    @classmethod
    def _segment_into_units(cls, lines: List[str]) -> List[Tuple[str, List[str]]]:
        units: List[Tuple[str, List[str]]] = []
        current_header = ""
        current_lines: List[str] = []

        for line in lines:
            match = cls.UNIT_HEADER_REGEX.match(line)
            if match:
                if current_header:
                    units.append((current_header, current_lines))
                current_header = line
                current_lines = []
            else:
                if current_header:
                    current_lines.append(line)

        if current_header:
            units.append((current_header, current_lines))

        return units

    @classmethod
    def _extract_topics_from_block(cls, lines: List[str], unit_number: int, unit_title: str) -> List[ParsedTopic]:
        topics: List[ParsedTopic] = []
        seen_ids = set()

        for line in lines:
            # Split line by bullets or semicolons, or dashes with surrounding spaces
            # Do NOT split hyphenated words like "Object-Oriented"
            raw_candidates = re.split(r'[;•\*]|\s+[-–—]\s+', line)

            for candidate in raw_candidates:
                cleaned = cls._clean_topic_string(candidate)
                if cls._is_valid_topic(cleaned):
                    topic_id = slugify(cleaned)
                    if topic_id and topic_id not in seen_ids:
                        seen_ids.add(topic_id)
                        topic = ParsedTopic(
                            id=topic_id,
                            name=cleaned,
                            unit_number=unit_number,
                            unit_title=unit_title
                        )
                        topics.append(topic)
        return topics

    @classmethod
    def _clean_topic_string(cls, text: str) -> str:
        t = text.strip()
        # Strip leading bullet punctuation, symbols, or unreadable chars (e.g. •, -, *, , ►, etc.)
        t = re.sub(r'^\s*[^a-zA-Z0-9\(\[\"\']+\s*', '', t)
        # Strip leading numbers/bullets like "1.1", "1.", "a)", "(2)"
        t = re.sub(r'^\s*([0-9]+[\.\)]|\([0-9]+\)|[a-z][\.\)])\s*', '', t, flags=re.IGNORECASE)
        t = re.sub(r'^\d+\s+', '', t)
        t = re.sub(r'^[ivxlcdmIVXLCDM]+[\.\)]\s*', '', t)
        # Strip trailing credit hours, marks, or CO mapping: "(3 hours)", "(10 Marks)", "[CO1]"
        t = re.sub(r'\s*\[\s*CO\s*\d[\d,\s]*\]', '', t, flags=re.IGNORECASE)
        t = re.sub(r'\s*(CO\s*\d[\d,\s]*)+$', '', t, flags=re.IGNORECASE)
        t = re.sub(r'\s*\(\s*\d+\s*(hours|hrs|marks|credits)?\s*\)\s*$', '', t, flags=re.IGNORECASE)
        # Strip trailing noise punctuation
        t = t.strip(" .,-:")
        return t.strip()

    @classmethod
    def _is_noise(cls, text: str) -> bool:
        t = text.strip()
        if not t:
            return True

        # All punctuation/numeric
        if re.fullmatch(r'[\d\s\-\u2013\u2014\.\,\(\)\*\+\/]+', t):
            return True

        # Prose sentence: > 15 words is too long to be a topic name
        words = t.split()
        if len(words) > 15:
            return True

        # Unbalanced trailing parenthesis fragment e.g. "order)"
        if t.endswith(')') and '(' not in t:
            return True

        for pat in cls._NOISE_PATS:
            if pat.search(t):
                return True

        return False

    @classmethod
    def _is_valid_topic(cls, text: str) -> bool:
        if not text or len(text) < 3 or len(text) > 100:
            return False

        if cls._is_noise(text):
            return False

        low = text.lower()
        ignore_keywords = [
            "unit", "module", "chapter", "syllabus", "textbook", "reference",
            "prerequisites:", "outcomes:", "hours", "marks", "exam", "assignment",
            "course", "subject", "code:"
        ]
        if any(low.startswith(kw) for kw in ignore_keywords):
            return False

        # If it contains a course code (e.g. "CS201: Data Structures...", "CS101", etc.)
        if cls.COURSE_CODE_REGEX.search(text):
            return False

        return True

