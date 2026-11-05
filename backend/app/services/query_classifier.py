from __future__ import annotations

import re

_FINANCIAL_DOMAIN_PATTERN = re.compile(
    r"\b(financ(?:e|ial)|budget|expenditure|expense|spend(?:ing)?|income|revenue|"
    r"surplus|deficit|allocation|allocated|remaining|utili[sz]ation|department|"
    r"institution|audit(?:or)?|anomal(?:y|ies)|forecast|transaction|grant|fund|"
    r"ledger|quarter|fiscal|report|overspent|overspend|risk|variance)\b",
    re.IGNORECASE,
)

# Numeric/aggregation intent — routed to SQL
_SQL_PATTERNS = [
    r"\btotal\s+income\b",
    r"\btotal\s+expenditure\b",
    r"\btotal\s+surplus\b",
    r"\btotal\s+budget\b",
    r"\bhow\s+much\b",
    r"\bwhich\s+department\s+(spent|has|had)\b",
    r"\b(highest|lowest|most|least|maximum|minimum|max|min)\b",
    r"\baverage\b",
    r"\bsum\s+of\b",
    r"\bhow\s+many\b",
    r"\bremaining\s+budget\b",
    r"\b(over[- ]?spent|overspend|overspent|over budget|budget violation)\b",
    r"\bbudget\s+utili[sz]ation\b.*\bpercent",
    r"\bspent\s+the\s+most\b",
r"\bspent\s+the\s+least\b",
r"\btop\s+department\b",
r"\bhighest\s+spending\b",
r"\blowest\s+spending\b",
r"\bcompare\b",
r"\bcomparison\b",
r"\bdepartment\s+wise\b",
r"\butilization\b",
r"\bvariance\b",
r"\bforecast\b",
r"\banomal(y|ies)\b",
r"\bwhich\s+department\b",
r"\bshow\s+me\b",
r"\blist\b",
r"\brank\b",
r"\branking\b",
]

# Analytical/explanatory intent — routed to RAG
_RAG_PATTERNS = [
    r"\bexplain\b",
    r"\bsummar(y|ize|ise)\b",
    r"\bdescribe\b",
    r"\bwhy\b",
    r"\brisk", 
    r"\banaly(sis|ze|se)\b",
    r"\bposition\b",
    r"\bobservation",
    r"\brecommend",
    r"\bconcern",
    r"\bqualitative\b",
    r"\bcontext\b",
]

_SQL_RE = [re.compile(p, re.IGNORECASE) for p in _SQL_PATTERNS]
_RAG_RE = [re.compile(p, re.IGNORECASE) for p in _RAG_PATTERNS]


def classify_query(question: str) -> str:
    """Returns 'sql', 'rag', 'hybrid', or 'unsupported'.

    'hybrid' is returned when the question shows strong signals of both
    (e.g. "Explain why total expenditure exceeded the budget") so the
    caller can compute the number AND retrieve supporting narrative context
    before answering — this is the common case for real auditor questions.
    """
    if not _FINANCIAL_DOMAIN_PATTERN.search(question):
        return "unsupported"

    sql_hit = any(p.search(question) for p in _SQL_RE)
    rag_hit = any(p.search(question) for p in _RAG_RE)

    if sql_hit and rag_hit:
        return "hybrid"
    if sql_hit:
        return "sql"
    if rag_hit:
        return "hybrid"
    # Financial questions without a recognized calculation or analysis intent
    # may still need context from uploaded reports.
    return "hybrid"
