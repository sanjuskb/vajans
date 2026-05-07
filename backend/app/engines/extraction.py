"""
VAJANS — LLM Extraction Engine (Phase 3)
==========================================
Uses LLM via OpenRouter to extract structured data
from retrieved document chunks.

CRITICAL DESIGN PRINCIPLE:
- LLM is ONLY used here for extraction (unstructured -> structured)
- LLM is NEVER used for evaluation/decisions (that's the Rule Engine)
- All outputs are schema-validated
- Regex is tried BEFORE LLM for well-defined field types (deterministic)
- If regex succeeds with high confidence, LLM call is skipped entirely
- If regex fails -> LLM is called -> regex fallback applied to not_found fields
- If still not found -> confidence=0.20, not_found=True
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx
import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.settings import settings

logger = structlog.get_logger("vajans.extraction")


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class ExtractedField:
    """One extracted value from a bidder document."""
    field_name:     str
    raw_value:      Optional[str]
    parsed_value:   Any
    unit:           Optional[str]
    source_snippet: Optional[str]
    confidence:     float
    not_found:      bool = False


@dataclass
class CriterionExtraction:
    """Extraction result for one criterion against one set of chunks."""
    criterion_id:    str
    criterion_label: str
    fields:          List[ExtractedField]
    raw_llm_output:  str
    model_used:      str


@dataclass
class ExtractionResult:
    """Complete extraction result for one bidder document."""
    job_id:         str
    file_id:        str
    bidder_name:    Optional[str]
    criteria_extractions: List[CriterionExtraction]
    extraction_warnings:  List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ExtractionError(Exception):
    def __init__(self, message: str, code: str = "EXTRACTION_ERROR"):
        self.code = code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_GST_PATTERN = re.compile(
    r'\b\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}Z[A-Z\d]{1}\b'
)

# Priority 1: Explicit average turnover statement (handles both inline and two-line formats)
_AVERAGE_TURNOVER_PATTERNS = [
    # "Average Annual Turnover (FY 2021-22 to FY 2023-24): Rs. 9.23 Crore" (inline with colon)
    re.compile(
        r'average\s+annual\s+turnover[^:\n]*:\s*(?:Rs\.?\s*)?(\d+\.?\d*)\s*(?:crore|Cr\.?)',
        re.IGNORECASE,
    ),
    # "Average Annual Turnover (3 years)\nRs. 9.23 Crore" (two-line: value on next line)
    re.compile(
        r'average\s+annual\s+turnover\s*(?:\([^)]*\))?\s*:?\s*\n+\s*(?:Rs\.?\s*)?(\d+\.?\d*)\s*(?:crore|Cr\.?)',
        re.IGNORECASE,
    ),
    # "3-year average: Rs. X Crore"
    re.compile(
        r'3[\s\-]?year\s+average[^:\n]*:\s*(?:Rs\.?\s*)?(\d+\.?\d*)\s*(?:crore|Cr\.?)',
        re.IGNORECASE,
    ),
    # "average turnover: Rs. X Crore"
    re.compile(
        r'average\s+turnover[^:\n]*:\s*(?:Rs\.?\s*)?(\d+\.?\d*)\s*(?:crore|Cr\.?)',
        re.IGNORECASE,
    ),
]

# Priority 2: FY year-amount pairs: "FY 2021-22: Rs. 8.20 Crore"
_FY_AMOUNT_PATTERN = re.compile(
    r'(?:FY\s*)?(?:20\d{2}[-–]\d{2,4})[^0-9]{0,40}(?:Rs\.?\s*)?(\d+\.?\d*)\s*(?:crore|Cr\.?)',
    re.IGNORECASE,
)

_LAKH_PATTERNS = [
    re.compile(r'(\d+\.?\d*)\s*(?:lakh|lakhs?|lac)', re.IGNORECASE),
]

_ISO_PATTERN        = re.compile(r'ISO\s*9001', re.IGNORECASE)
_EPF_PATTERN        = re.compile(
    r'(?:EPF|ESI|PF)\s*(?:registration\s+no\.?|number|no\.?|reg[a-z]*|code)?[:.\s]*([A-Z0-9/\-]+)',
    re.IGNORECASE,
)
_NOT_BLACKLISTED    = re.compile(r'not\s+(?:blacklisted|debarred|listed)', re.IGNORECASE)

# Match summary sentences in either word order:
#   "5 qualifying projects"
#   "Total qualifying projects: 6 (six)"
#   "qualifying projects completed: 5"
_QUALIFYING_PROJECTS_PATTERN = re.compile(
    r'(?:'
    r'(?P<n1>\d+)\s+qualifying\s+(?:similar\s+)?projects?'
    r'|'
    r'(?:total\s+)?qualifying\s+(?:similar\s+)?projects?'
    r'(?:\s+completed)?\s*[:\-]?\s*(?P<n2>\d+)'
    r')',
    re.IGNORECASE,
)
# "Total Completed Projects: 5 projects" / "Total Projects Completed: 5"
_TOTAL_PROJECTS_PATTERN = re.compile(
    r'total\s+(?:completed\s+)?projects?(?:\s+completed)?\s*[:\-]?\s*(\d+)',
    re.IGNORECASE,
)
# "Rs. X Crore" followed within 120 chars by a completion month/year
_PROJECT_AMOUNT_WITH_DATE_PATTERN = re.compile(
    r'(?:Rs\.?\s*)?(\d+\.?\d*)\s*(?:crore|Cr\.?)[^\n]{0,120}'
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December|20\d{2})',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Regex extraction functions
# ---------------------------------------------------------------------------

def _regex_extract_turnover(text: str) -> Optional[tuple]:
    """
    Return (value_in_crore, snippet) or None.

    Priority:
    1. Explicit "Average Annual Turnover: X Crore" statement
    2. Three FY year-amount pairs -> average them
    3. "annual turnover / turnover" keyword near a Crore figure
    4. Lakh values (last resort)
    """
    # P1 -- explicit average
    for pat in _AVERAGE_TURNOVER_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                val = float(m.group(1))
                snippet = text[max(0, m.start()): m.end() + 30].strip()
                return val, snippet
            except (ValueError, IndexError):
                continue

    # P2 -- FY year-amount pairs
    fy_matches = list(_FY_AMOUNT_PATTERN.finditer(text))
    if len(fy_matches) >= 2:
        try:
            vals = [float(m.group(1)) for m in fy_matches]
            avg = round(sum(vals) / len(vals), 2)
            snippet = "FY values: " + str(vals) + " -> avg " + str(avg) + " Crore"
            return avg, snippet
        except (ValueError, IndexError):
            pass

    # P3 -- "turnover" keyword near a Crore figure
    m = re.search(
        r'(?:annual\s+turnover|turnover|revenue\s+from\s+operations)'
        r'[^0-9]{0,60}(?:Rs\.?\s*)?(\d+\.?\d*)\s*(?:crore|Cr\.?)',
        text,
        re.IGNORECASE,
    )
    if m:
        try:
            val = float(m.group(1))
            snippet = text[max(0, m.start()): m.end() + 30].strip()
            return val, snippet
        except (ValueError, IndexError):
            pass

    # P4 -- lakh values
    for pat in _LAKH_PATTERNS:
        m = pat.search(text)
        if m:
            try:
                val = float(m.group(1)) / 100.0
                snippet = text[max(0, m.start() - 30): m.end() + 30].strip()
                return val, snippet
            except (ValueError, IndexError):
                continue
    return None


def _regex_extract_projects(text: str) -> Optional[ExtractedField]:
    """
    Count qualifying projects (value >= 2 Crore) using explicit patterns.

    Priority:
    1. "N qualifying projects" explicit summary
    2. "Total Completed Projects: N" explicit total
    3. Rs. X Crore amounts >= 2.0 appearing near completion dates
    """
    field_name = "projects"  # placeholder; caller sets real name

    # P1: Explicit "N qualifying projects" / "qualifying projects: N" statement
    m = _QUALIFYING_PROJECTS_PATTERN.search(text)
    if m:
        try:
            grp = m.group("n1") or m.group("n2")
            count = int(grp)
            snippet = "Qualifying projects: " + str(count)
            return ExtractedField(
                field_name=field_name,
                raw_value=snippet,
                parsed_value=count,
                unit="projects",
                source_snippet=snippet[:200],
                confidence=0.92,
                not_found=False,
            )
        except (ValueError, IndexError):
            pass

    # P2: "Total Completed Projects: N" explicit total
    m = _TOTAL_PROJECTS_PATTERN.search(text)
    if m:
        try:
            count = int(m.group(1))
            snippet = "Total completed projects: " + str(count)
            return ExtractedField(
                field_name=field_name,
                raw_value=snippet,
                parsed_value=count,
                unit="projects",
                source_snippet=snippet[:200],
                confidence=0.90,
                not_found=False,
            )
        except (ValueError, IndexError):
            pass

    # P3: Count "Rs. X Crore" amounts >= 2.0 near completion month/year
    qualifying = []
    for m in _PROJECT_AMOUNT_WITH_DATE_PATTERN.finditer(text):
        try:
            v = float(m.group(1))
            if v >= 2.0:
                qualifying.append(round(v, 1))
        except (ValueError, IndexError):
            continue

    # Deduplicate
    seen: set = set()
    deduped = []
    for v in qualifying:
        if v not in seen:
            seen.add(v)
            deduped.append(v)

    if deduped:
        count = len(deduped)
        snippet = "Projects >= 2 Cr near dates: " + str(deduped[:5])
        return ExtractedField(
            field_name=field_name,
            raw_value=snippet,
            parsed_value=count,
            unit="projects",
            source_snippet=snippet[:200],
            confidence=0.80,
            not_found=False,
        )

    return None


# Denial phrases used by the regex fallback (ISO / EPF) to detect explicit
# admissions that a certification or registration is absent.  Kept narrow so
# compliant bidders are never mis-flagged.
_REGEX_DENIAL_PHRASES = (
    "does not hold", "do not hold", "not held", "not hold",
    "not yet allotted", "not yet been allotted",
    "not yet issued",   "not yet been issued",
    "not yet certified", "not yet registered",
    "not currently certified", "not currently registered",
    "not registered",
    "no valid certificate", "no certification",
    "status: not held", "status: not registered",
    "certification status: not", "registration status: not",
    "application pending", "under process",
)


def _find_denial_in_text(
    text: str,
    anchor: int,
    *,
    window: int = 600,
) -> Optional[tuple[str, str]]:
    """Return (denial_phrase, evidence_snippet) if a denial phrase appears
    within `window` characters either side of `anchor`, else None.  Used by
    the ISO/EPF regex fallback so explicit "does not hold" / "not yet
    allotted" admissions surface as the parsed value (rather than being
    overridden by the default 'valid' / 'registered' label).
    """
    lo = max(0, anchor - window)
    hi = min(len(text), anchor + window)
    haystack = text[lo:hi]
    haystack_lower = haystack.lower()
    for phrase in _REGEX_DENIAL_PHRASES:
        idx = haystack_lower.find(phrase)
        if idx == -1:
            continue
        start = max(0, idx - 80)
        end   = min(len(haystack), idx + len(phrase) + 80)
        return phrase, haystack[start:end].strip()
    return None


def _regex_fallback(field_name: str, chunk_texts: List[str]) -> Optional[ExtractedField]:
    """
    Try regex extraction for a field when LLM returns not_found.
    Returns ExtractedField or None.
    """
    combined = "\n".join(chunk_texts)
    key = field_name.lower()

    # Turnover
    if any(k in key for k in ("turnover", "revenue", "financial")):
        result = _regex_extract_turnover(combined)
        if result:
            val, snippet = result
            return ExtractedField(
                field_name=field_name,
                raw_value=snippet[:200],
                parsed_value=val,
                unit="crore INR",
                source_snippet=snippet[:200],
                confidence=0.85,
                not_found=False,
            )

    # GST
    if any(k in key for k in ("gst", "gstin", "tax")):
        m = _GST_PATTERN.search(combined)
        if m:
            snippet = combined[max(0, m.start() - 20): m.end() + 20].strip()
            return ExtractedField(
                field_name=field_name,
                raw_value=m.group(),
                parsed_value=m.group(),
                unit=None,
                source_snippet=snippet[:200],
                confidence=0.90,
                not_found=False,
            )

    # ISO certification
    if any(k in key for k in ("iso", "certif", "quality")):
        iso_m = _ISO_PATTERN.search(combined)
        if iso_m:
            # Use AFFIRMATIVE expiry signals only — avoid matching "Not Expired"
            # which contains "Expired" but is actually PASS.
            # Look for unambiguous expiry patterns:
            cert_expired_m = re.search(
                r'certificate\s+expired',
                combined,
                re.IGNORECASE,
            )
            # "EXPIRED —" or "EXPIRED:" as a status indicator
            status_expired_m = re.search(
                r'\bEXPIRED\s*(?:—|-|:)',
                combined,
                re.IGNORECASE,
            )
            # "Status\nEXPIRED" table row
            table_expired_m = re.search(
                r'Status\s*\n+\s*EXPIRED\b',
                combined,
                re.IGNORECASE,
            )

            is_expired = bool(cert_expired_m or status_expired_m or table_expired_m)

            context = combined[max(0, iso_m.start() - 20): iso_m.end() + 120].strip()
            if is_expired:
                exp_ref = cert_expired_m or status_expired_m or table_expired_m
                if exp_ref:
                    snippet = combined[max(0, exp_ref.start() - 20): exp_ref.end() + 60].strip()
                else:
                    snippet = context
                return ExtractedField(
                    field_name=field_name,
                    raw_value=snippet[:200],
                    parsed_value="expired",
                    unit=None,
                    source_snippet=snippet[:200],
                    confidence=0.95,
                    not_found=False,
                )

            # Denial check: if the bid explicitly admits ISO is not held /
            # pending / under process, surface that as the parsed value so the
            # evaluator FAILs the criterion. Without this, a regex match on
            # "ISO 9001" anywhere in the text would default to "valid" even
            # for "does not hold a valid ISO 9001:2015 certificate".
            denial_hit = _find_denial_in_text(combined, iso_m.start())
            if denial_hit is not None:
                phrase, evidence = denial_hit
                return ExtractedField(
                    field_name=field_name,
                    raw_value=evidence[:200],
                    parsed_value=phrase,
                    unit=None,
                    source_snippet=evidence[:200],
                    confidence=0.92,
                    not_found=False,
                )

            return ExtractedField(
                field_name=field_name,
                raw_value=context[:200],
                parsed_value="valid",
                unit=None,
                source_snippet=context[:200],
                confidence=0.90,
                not_found=False,
            )

    # EPF / ESI
    if any(k in key for k in ("epf", "esi", "pf", "provident")):
        m = _EPF_PATTERN.search(combined)
        if m:
            snippet = combined[max(0, m.start() - 20): m.end() + 30].strip()
            # Denial check (analogous to ISO above): surface explicit denial
            # of EPF registration so it isn't silently treated as registered.
            denial_hit = _find_denial_in_text(combined, m.start())
            if denial_hit is not None:
                phrase, evidence = denial_hit
                return ExtractedField(
                    field_name=field_name,
                    raw_value=evidence[:200],
                    parsed_value=phrase,
                    unit=None,
                    source_snippet=evidence[:200],
                    confidence=0.92,
                    not_found=False,
                )
            return ExtractedField(
                field_name=field_name,
                raw_value=snippet[:200],
                parsed_value="registered",
                unit=None,
                source_snippet=snippet[:200],
                confidence=0.85,
                not_found=False,
            )

    # Blacklisting / debarment
    if any(k in key for k in ("blacklist", "debar", "integrity")):
        if _NOT_BLACKLISTED.search(combined):
            m = _NOT_BLACKLISTED.search(combined)
            snippet = combined[max(0, m.start() - 20): m.end() + 50].strip()
            return ExtractedField(
                field_name=field_name,
                raw_value=snippet[:200],
                parsed_value="not_blacklisted",
                unit=None,
                source_snippet=snippet[:200],
                confidence=0.90,
                not_found=False,
            )

    # Project count
    if any(k in key for k in ("project", "work", "experience", "similar")):
        ef = _regex_extract_projects(combined)
        if ef:
            ef.field_name = field_name
            return ef

    return None


def _regex_primary(field_name: str, chunk_texts: List[str]) -> Optional[ExtractedField]:
    """
    Attempt deterministic regex extraction BEFORE calling the LLM.
    Returns ExtractedField with confidence >= 0.85 for recognized field types,
    or None if the field type is not handled by regex.

    This eliminates LLM variability for well-defined structured fields.
    """
    key = field_name.lower()

    # Only attempt for known deterministic field types
    is_known = any(k in key for k in (
        "turnover", "revenue", "financial",
        "gst", "gstin", "tax",
        "iso", "certif", "quality",
        "epf", "esi", "pf", "provident",
        "blacklist", "debar", "integrity",
        "project", "work", "experience", "similar",
    ))

    if not is_known:
        return None

    return _regex_fallback(field_name, chunk_texts)


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a precise document extraction assistant for Indian government procurement evaluation.

Your ONLY job is to extract specific values from the provided document text.

CRITICAL RULES:
1. Extract ONLY information explicitly present in the provided text.
2. If a value is not found AND the document does not address the criterion at
   all, return null with not_found=true. NEVER fabricate.
3. If the document EXPLICITLY ADMITS the certification / registration is
   absent, expired, pending, in-process, not-yet-issued, applied-for, or
   "does not hold", you MUST return a non-null parsed_value capturing that
   denial -- e.g. "does not hold", "not yet allotted", "expired", "pending"
   -- and set not_found=false. This is a real extracted answer, not a miss.
4. For financial values: ALWAYS express in Crore INR (e.g., Rs. 8,20,000 = 0.082 Cr; Rs. 8.2 Cr = 8.2).
5. For turnover with multiple years: return the AVERAGE of the last 3 financial years in Crore.
6. For GST: return the full 15-character registration number.
7. For ISO 9001 / ISO 14001 / similar:
     - if the bid clearly states the cert is current/valid/in force -> parsed_value="valid"
     - if the bid says the cert is expired -> parsed_value="expired"
     - if the bid says it does NOT hold / not yet certified / pending -> parsed_value="does not hold"
8. For EPF / ESI:
     - if registered with a code -> parsed_value="registered"
     - if explicitly not yet allotted / pending / not yet issued -> parsed_value="not yet allotted"
9. For project count: return the INTEGER count of qualifying projects meeting the value threshold.
10. For non-blacklisting declaration: return parsed_value="not blacklisted" if
    the bidder declares a clean record, else parsed_value="blacklisted" if
    they admit any debarment/suspension.
11. Return ONLY valid JSON. No explanation, no markdown, no preamble.
12. Include a source_snippet (<= 200 chars) showing exactly where the value was found.
13. Set confidence between 0.0 and 1.0:
    - 0.90-0.95 = explicitly stated, single clear value
    - 0.80-0.89 = clearly present, minor interpretation
    - 0.70-0.79 = partial or contextual
    - 0.20 = not found anywhere in the text

INDIAN FINANCIAL DOCUMENT PATTERNS TO LOOK FOR:
- Turnover: "Annual Turnover", "Turnover", "Revenue from Operations", amounts followed by "Cr", "Crore", "Lakhs"
- GST: 15-character format like "29AABCI1234F1Z5"
- Projects: "Similar Work", "Completed Projects", project names with contract values
- Certifications: "ISO 9001", certificate numbers, validity dates
- EPF/ESI: "EPF Number", "ESI Code", "PF Registration"
"""


# ---------------------------------------------------------------------------
# LLM API call
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    reraise=True,
)
async def _call_llm(
    system_prompt: str,
    user_prompt: str,
    client: httpx.AsyncClient,
) -> str:
    payload = {
        "model": settings.LLM_MODEL,
        "temperature": 0.0,
        "seed": 42,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    response = await client.post(
        f"{settings.OPENROUTER_BASE_URL}/chat/completions",
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://vajans.ai",
            "X-Title": "VAJANS",
        },
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )

    if response.status_code != 200:
        raise ExtractionError(
            f"LLM API returned {response.status_code}: {response.text[:300]}",
            code="API_ERROR",
        )

    data = response.json()
    return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_extraction_prompt(
    criterion_label: str,
    criterion_description: str,
    fields_to_extract: List[Dict[str, str]],
    chunk_texts: List[str],
) -> str:
    context = "\n\n---\n\n".join(chunk_texts)
    fields_spec = json.dumps(fields_to_extract, indent=2)

    return (
        "CRITERION: " + criterion_label + "\n"
        "DESCRIPTION: " + criterion_description + "\n\n"
        "FIELDS TO EXTRACT:\n" + fields_spec + "\n\n"
        "IMPORTANT EXTRACTION HINTS:\n"
        "- For annual turnover: look for 'Average Annual Turnover' or FY year amounts. "
        "  Return the AVERAGE of the last 3 years in Crore.\n"
        "- For project count: count projects with value >= 2 Crore each. Return integer count.\n"
        "  If the bid states 'Total qualifying projects: N' or 'We have completed N qualifying projects', use N directly.\n"
        "- For GST: look for 15-character alphanumeric like '29AABCI1234F1Z5'\n"
        "- For ISO 9001 / similar certifications:\n"
        "    valid+in-force      -> parsed_value='valid'\n"
        "    expired             -> parsed_value='expired'\n"
        "    bidder admits NOT held / pending / under process -> parsed_value='does not hold'\n"
        "- For EPF/ESI:\n"
        "    has codes / registered -> parsed_value='registered'\n"
        "    'not yet issued' / 'not yet allotted' / 'pending' -> parsed_value='not yet allotted'\n"
        "- For blacklisting: parsed_value='not blacklisted' if company declares clean record;\n"
        "    parsed_value='blacklisted' if they admit any debarment.\n"
        "- Whenever the bid EXPLICITLY admits a mandatory cert/registration is absent,\n"
        "  pending or expired, set not_found=false and put the denial verbatim into parsed_value.\n\n"
        "DOCUMENT TEXT:\n" + context + "\n\n"
        "Return a JSON object with this EXACT structure:\n"
        '{\n'
        '  "fields": [\n'
        '    {\n'
        '      "field_name": "<name from fields_to_extract>",\n'
        '      "raw_value": "<exact text as found, or null>",\n'
        '      "parsed_value": <normalized value: number/string/null>,\n'
        '      "unit": "<unit or null>",\n'
        '      "source_snippet": "<<=200 chars where found, or null>",\n'
        '      "confidence": <0.20 if not found, 0.80-0.95 if found>,\n'
        '      "not_found": <true if absent, false if found>\n'
        '    }\n'
        '  ]\n'
        '}'
    )


# ---------------------------------------------------------------------------
# Extraction engine
# ---------------------------------------------------------------------------

async def extract_criterion_fields(
    criterion_id: str,
    criterion_label: str,
    criterion_description: str,
    fields_to_extract: List[Dict[str, str]],
    retrieved_chunks: List[str],
) -> CriterionExtraction:
    """
    Extract specific fields for one criterion from retrieved chunks.

    Flow:
    1. Try regex-primary for each field (deterministic, no LLM cost)
    2. If all fields resolved by regex -> skip LLM entirely
    3. Otherwise call LLM for remaining fields
    4. Apply regex fallback for any LLM not_found results
    """
    log = logger.bind(criterion_id=criterion_id)
    log.info("Extracting fields for criterion", chunks=len(retrieved_chunks))

    if not retrieved_chunks:
        log.warning("No chunks provided -- all fields will be not_found")
        return CriterionExtraction(
            criterion_id=criterion_id,
            criterion_label=criterion_label,
            fields=[
                ExtractedField(
                    field_name=f["field_name"],
                    raw_value=None,
                    parsed_value=None,
                    unit=None,
                    source_snippet=None,
                    confidence=0.20,
                    not_found=True,
                )
                for f in fields_to_extract
            ],
            raw_llm_output="",
            model_used=settings.LLM_MODEL,
        )

    # Step 1: Try regex-primary for all fields
    regex_results: dict[str, ExtractedField] = {}
    fields_needing_llm = []

    for f_spec in fields_to_extract:
        fname = f_spec["field_name"]
        regex_ef = _regex_primary(fname, retrieved_chunks)
        if regex_ef is not None and not regex_ef.not_found:
            regex_ef.field_name = fname
            regex_results[fname] = regex_ef
            log.debug(
                "Regex-primary succeeded",
                field=fname,
                value=regex_ef.parsed_value,
                confidence=regex_ef.confidence,
            )
        else:
            fields_needing_llm.append(f_spec)

    # Step 2: If regex resolved everything, skip LLM entirely
    if not fields_needing_llm:
        log.info(
            "All fields resolved by regex -- LLM call skipped",
            count=len(regex_results),
        )
        return CriterionExtraction(
            criterion_id=criterion_id,
            criterion_label=criterion_label,
            fields=list(regex_results.values()),
            raw_llm_output="(regex-only extraction)",
            model_used="regex",
        )

    # Step 3: Call LLM for remaining fields
    user_prompt = _build_extraction_prompt(
        criterion_label=criterion_label,
        criterion_description=criterion_description,
        fields_to_extract=fields_needing_llm,
        chunk_texts=retrieved_chunks,
    )

    raw_output = ""
    async with httpx.AsyncClient() as client:
        try:
            raw_output = await _call_llm(SYSTEM_PROMPT, user_prompt, client)
        except Exception as exc:
            log.warning("LLM call failed -- using regex fallback only", error=str(exc))
            # LLM failed: fall back to regex for the remaining fields
            final_fields = list(regex_results.values())
            for f_spec in fields_needing_llm:
                fname = f_spec["field_name"]
                fb = _regex_fallback(fname, retrieved_chunks)
                if fb:
                    fb.field_name = fname
                    final_fields.append(fb)
                else:
                    final_fields.append(ExtractedField(
                        field_name=fname,
                        raw_value=None,
                        parsed_value=None,
                        unit=None,
                        source_snippet=None,
                        confidence=0.20,
                        not_found=True,
                    ))
            return CriterionExtraction(
                criterion_id=criterion_id,
                criterion_label=criterion_label,
                fields=final_fields,
                raw_llm_output="",
                model_used="regex-fallback",
            )

    # Step 4: Parse LLM output (pass chunks so the denial-override can scan
    # the full retrieved context, not just the LLM-truncated snippet).
    llm_fields = _parse_llm_output(
        raw_output, fields_needing_llm, criterion_id,
        retrieved_chunks=retrieved_chunks,
    )

    # Step 5: For LLM not_found, apply regex fallback
    final_fields = list(regex_results.values())
    for ef in llm_fields:
        if ef.not_found or ef.parsed_value is None:
            fb = _regex_fallback(ef.field_name, retrieved_chunks)
            if fb is not None:
                log.info(
                    "Regex fallback succeeded after LLM not_found",
                    field=ef.field_name,
                    value=fb.parsed_value,
                )
                final_fields.append(fb)
            else:
                ef.confidence = 0.20
                ef.not_found = True
                final_fields.append(ef)
        else:
            final_fields.append(ef)

    log.info(
        "Criterion extraction complete",
        fields_extracted=len([f for f in final_fields if not f.not_found]),
        fields_not_found=len([f for f in final_fields if f.not_found]),
        llm_used=True,
    )

    return CriterionExtraction(
        criterion_id=criterion_id,
        criterion_label=criterion_label,
        fields=final_fields,
        raw_llm_output=raw_output,
        model_used=settings.LLM_MODEL,
    )


def _parse_llm_output(
    raw_output: str,
    expected_fields: List[Dict[str, str]],
    criterion_id: str,
    retrieved_chunks: Optional[List[str]] = None,
) -> List[ExtractedField]:
    """Parse and validate LLM JSON output."""
    try:
        data = json.loads(raw_output)
        llm_fields = data.get("fields", [])
    except json.JSONDecodeError as exc:
        logger.error(
            "LLM output is not valid JSON",
            criterion_id=criterion_id,
            error=str(exc),
            raw_output=raw_output[:200],
        )
        return [
            ExtractedField(
                field_name=f["field_name"],
                raw_value=None,
                parsed_value=None,
                unit=None,
                source_snippet=None,
                confidence=0.20,
                not_found=True,
            )
            for f in expected_fields
        ]

    llm_field_map = {f.get("field_name"): f for f in llm_fields if isinstance(f, dict)}
    results: List[ExtractedField] = []

    for expected in expected_fields:
        fname = expected["field_name"]
        llm_f = llm_field_map.get(fname, {})

        raw_val = llm_f.get("raw_value")
        snippet = llm_f.get("source_snippet")
        pv      = llm_f.get("parsed_value")
        not_fnd = bool(llm_f.get("not_found", raw_val is None))

        if pv is None or (isinstance(pv, str) and pv.lower() in ("none", "null", "")):
            pv = None
            not_fnd = True

        # Post-LLM denial override.  Mitigates a gpt-4o-mini failure mode in
        # which the model grabs a nearby presence word ("valid", "registered")
        # even when the surrounding retrieved text explicitly admits the
        # certification is absent.  For `contains`-style fields (ISO, EPF/ESI,
        # etc.) we scan the verbatim snippet AND the full retrieved chunks
        # for unambiguous denial phrases; if found we overwrite parsed_value
        # with the denial so the downstream evaluator marks the criterion FAIL.
        pv, not_fnd, snippet = _apply_denial_override(
            field_name=fname,
            parsed_value=pv,
            not_found=not_fnd,
            snippet=snippet,
            retrieved_chunks=retrieved_chunks,
        )

        confidence = float(llm_f.get("confidence", 0.20))

        if raw_val and not snippet:
            confidence = min(confidence, 0.65)

        if not_fnd or pv is None:
            confidence = min(confidence, 0.20)

        confidence = max(0.0, min(1.0, confidence))

        results.append(ExtractedField(
            field_name=fname,
            raw_value=raw_val,
            parsed_value=pv,
            unit=llm_f.get("unit"),
            source_snippet=snippet,
            confidence=confidence,
            not_found=not_fnd,
        ))

    return results


# Presence-check fields whose parsed_value should reflect explicit denials
# found in the source snippet. The list is intentionally TIGHT -- generic
# tokens like "registration" or "certificate" would over-match (e.g. a
# bidder's GST registration field whose retrieved chunk happens to also
# contain ISO denial text).  Add a specific token only when you have
# verified the denial-override semantics for that criterion.
_DENIAL_CHECK_KEY_HINTS = (
    "iso", "iso_9001", "iso_14001", "iso_45001",
    "epf", "esi", "pf_registration", "pf_esi",
    "labour_law_compliance", "labour_compliance",
)

# Unambiguous denial phrases. Any hit forces the parsed_value to the denial
# verbatim so the evaluator's FAIL signals catch it.  Keep this list tight --
# false positives here would penalise compliant bidders.
_SNIPPET_DENIAL_PATTERNS = (
    "does not hold",           "do not hold",
    "not yet allotted",        "not yet been allotted",
    "not yet issued",          "not yet been issued",
    "not yet certified",       "not yet registered",
    "not currently certified", "not currently registered",
    "not held",                "not hold",
    "not registered",
    "no valid certificate",    "no certification",
    "certification status: not",
    "status: not held",        "status: not registered",
    "registration status: not",
    "application pending",     "under process",
    "pending since",
)


def _apply_denial_override(
    *,
    field_name: str,
    parsed_value: Any,
    not_found: bool,
    snippet: str | None,
    retrieved_chunks: Optional[List[str]] = None,
) -> tuple[Any, bool, Optional[str]]:
    """If the retrieved text explicitly denies a mandatory cert/registration,
    replace the LLM's parsed_value with the denial verbatim so the evaluator
    fails it.  Only runs for fields that look like presence/compliance checks.
    Returns (parsed_value, not_found, snippet) -- snippet may be rewritten to
    a ~200-char window around the matched denial so audit evidence is useful.
    """
    key = (field_name or "").lower()
    if not any(h in key for h in _DENIAL_CHECK_KEY_HINTS):
        return parsed_value, not_found, snippet
    # Ignore blacklisting: "is NOT blacklisted" is a COMPLIANT declaration.
    if "blacklist" in key or "debar" in key:
        return parsed_value, not_found, snippet

    # Search the LLM-returned snippet first (fast path), then fall back to
    # the full retrieved chunks so truncated snippets don't hide denials.
    haystacks: List[tuple[str, str]] = []
    if snippet and isinstance(snippet, str):
        haystacks.append(("snippet", snippet))
    if retrieved_chunks:
        haystacks.append(("chunk", "\n\n".join(retrieved_chunks)))

    for source, hay in haystacks:
        hay_lower = hay.lower()
        for phrase in _SNIPPET_DENIAL_PATTERNS:
            idx = hay_lower.find(phrase)
            if idx == -1:
                continue
            # Build a readable evidence window around the match (up to 200 chars).
            window_start = max(0, idx - 80)
            window_end   = min(len(hay), idx + len(phrase) + 80)
            evidence     = hay[window_start:window_end].strip()
            logger.info(
                "Denial override applied",
                field=field_name,
                phrase=phrase,
                source=source,
                original_parsed=parsed_value,
            )
            # Return the denial phrase as parsed_value so evaluator FAILs it,
            # and surface the surrounding text as the audit snippet.
            return phrase, False, evidence[:200]
    return parsed_value, not_found, snippet


# ---------------------------------------------------------------------------
# Tender criteria extraction
# ---------------------------------------------------------------------------

TENDER_CRITERIA_SYSTEM_PROMPT = """You are a precise Indian government tender document analyst.
Extract all eligibility criteria from the provided tender document text.

RULES:
1. Return ONLY valid JSON. No explanation outside JSON.
2. Identify EVERY eligibility criterion, no matter how minor.
   You MUST include compliance / certification / integrity criteria as
   SEPARATE entries when they are presented in distinct sections of the
   tender, even if they share an operator. Examples that always become
   their own criterion when present in the tender:
       - GST registration              -> id="gst_registration"
       - ISO 9001 / ISO 14001 / etc.   -> id="iso_9001_certification"
       - EPF / ESI registration        -> id="epf_esi_registration"
       - Not blacklisted / debarred    -> id="not_blacklisted"
       - PAN / TAN / Trade licence     -> id="<respective>_registration"
       - Bid security / EMD            -> id="bid_security"
       - Performance security          -> id="performance_security"
3. Distinguish mandatory (shall/must/essential/MANDATORY) from preferred
   (should/preferred/desirable).
4. For numeric thresholds: extract the number and unit separately.
   - Turnover thresholds: express in Crore INR (e.g., "5 Crore" -> threshold_value=5, threshold_unit="crore INR")
   - Project thresholds: express as count (e.g., "3 similar works" -> threshold_value=3, threshold_unit="projects")
5. For time windows: extract in years (e.g., "last 5 years" -> 5).
6. Set operator:
   - "gte" for minimum thresholds (turnover >= X, at least N projects)
   - "lte" for upper bounds
   - "contains" for presence / certification / declaration checks
     (GST registered, ISO certified, EPF/ESI registered, not blacklisted)
7. Set threshold_value=null for `contains` criteria. Set
   ambiguous=true ONLY if the threshold is truly unclear -- never set
   ambiguous=true merely because the criterion is a certification or
   declaration.
"""


async def extract_tender_criteria(tender_text: str) -> Dict[str, Any]:
    """Extract all eligibility criteria from a tender document."""
    log = logger.bind(tender_chars=len(tender_text))
    log.info("Extracting tender criteria")

    user_prompt = (
        "Extract all eligibility criteria from this tender document.\n\n"
        "Return JSON with this structure:\n"
        '{\n'
        '  "criteria": [\n'
        '    {\n'
        '      "id": "<slug like annual_turnover_min>",\n'
        '      "label": "<human readable label>",\n'
        '      "criterion_type": "<financial|technical|compliance|certification>",\n'
        '      "description": "<full criterion description>",\n'
        '      "mandatory": <true|false>,\n'
        '      "threshold_value": <number or null>,\n'
        '      "threshold_unit": "<unit or null>",\n'
        '      "time_window_years": <number or null>,\n'
        '      "operator": "<gte|lte|eq|contains or null>",\n'
        '      "ambiguous": <true ONLY if threshold is truly unclear, otherwise false>,\n'
        '      "source_snippet": "<=200 chars from document"\n'
        '    }\n'
        '  ]\n'
        '}\n\n'
        "IMPORTANT:\n"
        "- For turnover criteria: threshold_value in Crore (e.g., 5 Crore = 5, NOT 5000000)\n"
        "- For project count: threshold_value = count (e.g., '3 similar works' = 3)\n"
        "- For certifications (GST, ISO, EPF/ESI, blacklisting): "
        "threshold_value=null, operator='contains', mandatory=true\n"
        "- Each separately documented compliance / certification / integrity\n"
        "  criterion (B.3 GST, B.4 ISO, B.5 EPF/ESI, B.6 blacklisting, etc.)\n"
        "  MUST appear as its own JSON entry. Do NOT merge them.\n"
        "- Set ambiguous=false for all standard criteria unless truly uninterpretable\n"
        "- Do NOT set ambiguous=true just because the criterion is for a certification\n\n"
        "TENDER DOCUMENT:\n" + tender_text[:24000]
    )

    async with httpx.AsyncClient() as client:
        try:
            raw = await _call_llm(TENDER_CRITERIA_SYSTEM_PROMPT, user_prompt, client)

            try:
                data = json.loads(raw)
            except Exception as exc:
                logger.error("JSON parsing failed", error=str(exc))
                data = {"criteria": []}

            criteria = data.get("criteria", [])
            log.info("Tender criteria extracted", count=len(criteria))
            return data
        except Exception as exc:
            raise ExtractionError(
                f"Tender criteria extraction failed: {exc}",
                code="CRITERIA_EXTRACTION_FAILED",
            ) from exc


def extract_tender_criteria_sync(tender_text: str) -> Dict[str, Any]:
    """Sync wrapper for Celery task usage."""
    import asyncio
    return asyncio.run(extract_tender_criteria(tender_text))
