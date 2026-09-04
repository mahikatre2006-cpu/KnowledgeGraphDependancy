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
    Uses regex patterns to identify unit blocks and individual topics.
    """

    # Regex patterns for unit / module header detection
    UNIT_HEADER_REGEX = re.compile(
        r'^(?:unit|module|chapter|part|section)\s*[-:]?\s*([0-9ivxlcdm]+|\w+)\s*[-:]?\s*(.*)$',
        re.IGNORECASE
    )

    COURSE_CODE_REGEX = re.compile(r'\b([A-Z]{2,4}\s*[-:]?\s*\d{3,4})\b', re.IGNORECASE)

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

        # 1. Detect Course Code & Title
        course_code = cls._extract_course_code(text)
        course_title = cls._extract_course_title(lines)

        # 2. Segment lines into Unit blocks
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

        # If no units were detected via regex headers, treat full text as Unit 1
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
            if not cls.UNIT_HEADER_REGEX.match(line) and len(line) > 3 and len(line) < 80:
                # Strip course codes like CS101: or CS 201 -
                clean = re.sub(r'^[A-Z]{2,4}\s*[-:]?\s*\d{3,4}\s*[:|-]?\s*', '', line, flags=re.IGNORECASE)
                clean = re.sub(r'^(course|syllabus|subject)\s*[:|-]\s*', '', clean, flags=re.IGNORECASE)
                return clean.strip()
        return "Course Syllabus"

    @classmethod
    def _segment_into_units(cls, lines: List[str]) -> List[Tuple[str, List[str]]]:
        units: List[Tuple[str, List[str]]] = []
        current_header = ""
        current_lines: List[str] = []

        for line in lines:
            match = cls.UNIT_HEADER_REGEX.match(line)
            if match:
                if current_header or current_lines:
                    units.append((current_header or "Overview", current_lines))
                current_header = line
                current_lines = []
            else:
                current_lines.append(line)

        if current_header or current_lines:
            units.append((current_header or "Overview", current_lines))

        return units

    @classmethod
    def _extract_topics_from_block(cls, lines: List[str], unit_number: int, unit_title: str) -> List[ParsedTopic]:
        topics: List[ParsedTopic] = []
        seen_ids = set()

        for line in lines:
            # Split line by bullets, semicolons, commas, or dashes if long
            raw_candidates = re.split(r'[;•\*]|\b-\b', line)
            
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
        # Strip leading numbers/bullets like "1.1", "a)", "(2)", "-", "•"
        cleaned = re.sub(r'^\s*([0-9]+[\.\)]|\([0-9]+\)|[a-z][\.\)]|[-•\*\:\–])\s*', '', text, flags=re.IGNORECASE)
        # Strip trailing credit hours or noise like "(3 hours)", "(10 Marks)"
        cleaned = re.sub(r'\s*\(\s*\d+\s*(hours|hrs|marks|credits)?\s*\)', '', cleaned, flags=re.IGNORECASE)
        # Strip trailing punctuation
        cleaned = cleaned.strip(" .,-:")
        return cleaned.strip()

    @classmethod
    def _is_valid_topic(cls, text: str) -> bool:
        if not text or len(text) < 3 or len(text) > 75:
            return False
        # Filter out common syllabus metadata headers
        low = text.lower()
        ignore_keywords = [
            "unit", "module", "chapter", "syllabus", "textbook", "reference",
            "prerequisites:", "outcomes:", "hours", "marks", "exam", "assignment",
            "course", "subject", "code:"
        ]
        if any(low.startswith(kw) for kw in ignore_keywords):
            return False
        # Also filter out lines that match course code patterns (e.g. "CS201: Data Structures...")
        if cls.COURSE_CODE_REGEX.search(text):
            return False
        return True
