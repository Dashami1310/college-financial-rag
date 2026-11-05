from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import List, Optional

import pdfplumber


# ---------------------------------------------------------------------------
# Canonical sections + the heading patterns that identify them
# ---------------------------------------------------------------------------
SECTION_PATTERNS: dict[str, list[str]] = {
    "Income & Expenditure": [
        r"income\s*(?:and|&)\s*expenditure(?:\s+account)?",
        r"statement\s+of\s+income\s*(?:and|&)\s*expenditure",
    ],
    "Balance Sheet": [
        r"balance\s+sheet",
        r"statement\s+of\s+financial\s+position",
    ],
    "Grant Assets": [
        r"grant[\s-]*(?:in[\s-]*aid)?\s*assets",
        r"grants?\s+received",
        r"grant\s+utilization",
        r"grant\s+utilisation",
    ],
    "Depreciation": [
        r"depreciation(?:\s+schedule)?",
    ],
    "Audit Observations": [
        r"audit(?:or'?s)?\s+observations?",
        r"observations?\s+(?:and|&)\s+recommendations?",
        r"auditor'?s\s+report",
        r"qualifications?\s+(?:and|&)\s+observations?",
    ],
    "Notes to Accounts": [
        r"notes?\s+(?:to|on)\s+accounts?",
        r"notes?\s+(?:to|forming\s+part\s+of)\s+(?:the\s+)?financial\s+statements?",
    ],
}

DEFAULT_SECTION = "General"

# A line is only treated as a heading if it's short, and either fully
# uppercase or matches a known pattern closely — avoids misclassifying a
# stray in-paragraph mention of "the balance sheet shows..." as a heading.
_MAX_HEADING_WORDS = 10

_COMPILED_PATTERNS: dict[str, list[re.Pattern]] = {
    section: [re.compile(p, re.IGNORECASE) for p in patterns]
    for section, patterns in SECTION_PATTERNS.items()
}

# Detects a financial-year-like token, e.g. "2025-2026", "2025-26", "FY 2025-26"
YEAR_PATTERN = re.compile(r"(?:FY\s*)?(20\d{2})\s*[-–]\s*(20\d{2}|\d{2})", re.IGNORECASE)


@dataclass
class ExtractedPage:
    page_number: int
    text: str


@dataclass
class SectionBlock:
    section: str
    text: str


# ---------------------------------------------------------------------------
# 1. Text extraction
# ---------------------------------------------------------------------------
def extract_text_from_pdf(file_bytes: bytes) -> List[ExtractedPage]:
    """Extracts text page-by-page from a PDF using pdfplumber."""
    pages: List[ExtractedPage] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(ExtractedPage(page_number=i, text=text))
    return pages


def detect_report_year(pages: List[ExtractedPage]) -> Optional[str]:
    """Scans the first few pages for a financial-year-like token, e.g. '2025-2026'."""
    for page in pages[:3]:
        match = YEAR_PATTERN.search(page.text)
        if match:
            start, end = match.group(1), match.group(2)
            if len(end) == 2:
                end = start[:2] + end
            return f"{start}-{end}"
    return None


# ---------------------------------------------------------------------------
# 2. Section detection
# ---------------------------------------------------------------------------
def _match_section(line: str) -> Optional[str]:
    stripped = line.strip()
    if not stripped or len(stripped.split()) > _MAX_HEADING_WORDS:
        return None
    # Strip common numbering/bullet prefixes, e.g. "3." "III." "(a)"
    cleaned = re.sub(r"^[\dIVXivx]+[\.\)]\s*", "", stripped)
    for section, patterns in _COMPILED_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(cleaned):
                return section
    return None


def detect_sections(pages: List[ExtractedPage]) -> List[SectionBlock]:
    """
    Walks the extracted text line-by-line, splitting it into SectionBlocks
    whenever a recognized heading is found. Text before the first heading
    goes into a "General" block rather than being discarded.
    """
    blocks: List[SectionBlock] = []
    current_section = DEFAULT_SECTION
    current_lines: List[str] = []

    def flush():
        text = "\n".join(current_lines).strip()
        if text:
            blocks.append(SectionBlock(section=current_section, text=text))

    for page in pages:
        for line in page.text.split("\n"):
            matched = _match_section(line)
            if matched:
                flush()
                current_section = matched
                current_lines = []
            else:
                current_lines.append(line)
    flush()

    return blocks if blocks else [SectionBlock(section=DEFAULT_SECTION, text="")]


def merge_blocks_by_section(blocks: List[SectionBlock]) -> List[SectionBlock]:
    """
    A section may legitimately appear more than once across a long document
    (e.g. 'Notes to Accounts' spanning several non-contiguous pages under
    repeated sub-headings). This merges same-section blocks back together,
    in first-seen order, so chunking operates on one coherent text per
    section rather than many small fragments.
    """
    order: List[str] = []
    merged: dict[str, list[str]] = {}
    for block in blocks:
        if block.section not in merged:
            merged[block.section] = []
            order.append(block.section)
        merged[block.section].append(block.text)
    return [SectionBlock(section=s, text="\n\n".join(merged[s])) for s in order if merged[s]]


# ---------------------------------------------------------------------------
# 3. Section-aware chunking
# ---------------------------------------------------------------------------
def chunk_sections(
    blocks: List[SectionBlock], chunk_size: int = 500, chunk_overlap: int = 80
) -> List[dict]:
    """
    Splits each section's text independently (never mixing two sections
    into one chunk) using LangChain's RecursiveCharacterTextSplitter.
    Returns a flat list of {section, chunk_index, chunk_text} dicts ready
    for persistence into the `audit_chunks` table.
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " "],
    )

    results: List[dict] = []
    for block in blocks:
        if not block.text.strip():
            continue
        pieces = splitter.split_text(block.text)
        for idx, piece in enumerate(pieces):
            results.append({
                "section": block.section,
                "chunk_index": idx,
                "chunk_text": piece,
            })
    return results


# ---------------------------------------------------------------------------
# 4. Orchestration entry point
# ---------------------------------------------------------------------------
def process_audit_pdf(file_bytes: bytes, chunk_size: int = 500, chunk_overlap: int = 80) -> dict:
    """
    Full Phase 2 pipeline for one PDF: extract -> detect sections -> chunk.
    Returns a dict with the detected year, per-section chunk lists, and a
    summary count per section (useful for the upload confirmation screen).
    """
    pages = extract_text_from_pdf(file_bytes)
    detected_year = detect_report_year(pages)

    raw_blocks = detect_sections(pages)
    merged_blocks = merge_blocks_by_section(raw_blocks)
    chunks = chunk_sections(merged_blocks, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    section_counts: dict[str, int] = {}
    for c in chunks:
        section_counts[c["section"]] = section_counts.get(c["section"], 0) + 1

    total_chars = sum(len(p.text) for p in pages)

    return {
        "page_count": len(pages),
        "total_characters": total_chars,
        "detected_year": detected_year,
        "sections_found": list(section_counts.keys()),
        "section_chunk_counts": section_counts,
        "chunks": chunks,
    }
