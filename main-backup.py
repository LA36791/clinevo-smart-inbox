from datetime import datetime, timezone
import re
import time

import fitz
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(
    title="Clinevo Smart Inbox AI Service",
    version="1.2.0"
)


# ============================================================
# MODELS
# ============================================================

class AnalyzeRequest(BaseModel):
    message_id: str = ""
    sender: str = ""
    subject: str = ""
    date: str = ""
    body: str = ""
    attachments: list[str] = Field(default_factory=list)


class ExtractedFact(BaseModel):
    field: str
    value: str
    confidence: float
    source: str


class AnalyzeResponse(BaseModel):
    categories: list[str]
    classification_confidence: float
    reason: str
    facts: list[ExtractedFact]
    human_review_required: bool
    processing_time_ms: int
    processed_at: str


class PageEvidence(BaseModel):
    page_number: int
    text: str
    confidence: float
    source: str


class DocumentFact(BaseModel):
    field: str
    value: str
    confidence: float
    source: str
    page_number: int


class DocumentAnalysisResponse(BaseModel):
    filename: str
    page_count: int
    document_type: str
    extracted_text: str
    evidence: list[PageEvidence]
    facts: list[DocumentFact]
    categories: list[str]
    classification_confidence: float
    classification_reason: str
    document_summary: str
    human_review_required: bool
    processing_time_ms: int
    processed_at: str


# ============================================================
# COMMON HELPERS
# ============================================================

NOT_STATED = "Not stated"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_value(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "")
    return value.strip(" \t\r\n.,;:-")


def extract_field(text: str, labels: list[str]):
    """Conservative Label: Value extraction."""
    for label in labels:
        pattern = rf"^\s*{re.escape(label)}\s*:\s*(.+?)\s*$"

        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.MULTILINE
        )

        if match and match.group(1).strip():
            return clean_value(match.group(1)), 0.95

    return NOT_STATED, 0.0


def regex_extract(
    text: str,
    patterns: list[str],
    confidence: float = 0.90
):
    """Extract the first explicit natural-language match."""

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.MULTILINE
        )

        if match:
            value = clean_value(match.group(1))

            if value:
                return value, confidence

    return NOT_STATED, 0.0


def fact(
    field: str,
    value: str,
    confidence: float,
    source: str
) -> ExtractedFact:

    return ExtractedFact(
        field=field,
        value=value,
        confidence=round(confidence, 2),
        source=source
    )


# ============================================================
# CLASSIFICATION
# ============================================================

def classify_text(text: str):

    lower = text.lower()

    scores = {
        "SAFETY_REPORT_ICSR": 0.0,
        "QUALITY_COMPLAINT_PQC": 0.0,
        "INFO_REQUEST_MI": 0.0
    }

    safety_strong = [
        "adverse event",
        "adverse reaction",
        "side effect",
        "suspected adverse",
        "patient experienced",
        "patient developed",
        "patient received",
        "icsr",
        "safety report",
        "reaction",
        "hospitalization",
        "hospitalised",
        "hospitalized"
    ]

    safety_support = [
        "patient",
        "severity",
        "serious",
        "non-serious",
        "reporter",
        "reaction"
    ]

    quality_strong = [
        "quality complaint",
        "product complaint",
        "quality issue",
        "product defect",
        "defective product",
        "damaged product",
        "wrong product",
        "foreign material",
        "leaking",
        "broken",
        "contamination",
        "complaint about product",
        "incorrect label",
        "wrong label",
        "packaging damaged",
        "packaging defect"
    ]

    quality_support = [
        "lot number",
        "lot",
        "batch number",
        "batch",
        "packaging defect",
        "label defect",
        "tablet broken",
        "container damaged",
        "damaged packaging"
    ]

    medical_strong = [
        "medical information",
        "information request",
        "information inquiry",
        "medical inquiry",
        "request for information",
        "what is the dose",
        "what dose",
        "dosage",
        "recommended dosage",
        "administration",
        "how should",
        "how to use",
        "contraindication",
        "drug interaction",
        "product information",
        "clinical information",
        "clinical data",
        "indication",
        "indications",
        "known interaction"
    ]

    for term in safety_strong:
        if term in lower:
            scores["SAFETY_REPORT_ICSR"] += 2.0

    for term in safety_support:
        if term in lower:
            scores["SAFETY_REPORT_ICSR"] += 0.5

    for term in quality_strong:
        if term in lower:
            scores["QUALITY_COMPLAINT_PQC"] += 2.5

    for term in quality_support:
        if term in lower:
            scores["QUALITY_COMPLAINT_PQC"] += 0.5

    for term in medical_strong:
        if term in lower:
            scores["INFO_REQUEST_MI"] += 2.5

    # Batch/lot alone must not turn an ICSR into PQC.
    if scores["SAFETY_REPORT_ICSR"] > 0:

        quality_only_terms = [
            "quality complaint",
            "product complaint",
            "quality issue",
            "product defect",
            "defective product",
            "damaged product",
            "wrong product",
            "packaging defect",
            "label defect",
            "incorrect label",
            "wrong label"
        ]

        has_quality_signal = any(
            term in lower
            for term in quality_only_terms
        )

        if not has_quality_signal:
            scores["QUALITY_COMPLAINT_PQC"] = min(
                scores["QUALITY_COMPLAINT_PQC"],
                0.5
            )

    # No meaningful signal.
    if max(scores.values()) == 0:

        return (
            ["NOT_RELEVANT"],
            0.50,
            "No strong healthcare safety, quality complaint, or medical-information signal was detected."
        )

    max_score = max(scores.values())

    categories = [
        category
        for category, score in scores.items()
        if score >= max_score * 0.70 and score > 0
    ]

    categories = [
        category
        for category in categories
        if scores[category] >= 1.5
    ]

    if not categories:
        categories = [
            max(scores, key=scores.get)
        ]

    confidence = min(
        0.95,
        0.70 + (max_score * 0.04)
    )

    if len(categories) > 1:

        confidence = min(
            confidence,
            0.78
        )

        reason = (
            "Multiple domain signals were detected. "
            "Human review is recommended to confirm the applicable workflow."
        )

    else:

        category = categories[0]

        reason_map = {
            "SAFETY_REPORT_ICSR":
                "Patient/reaction/safety signals support routing to Safety Report / ICSR.",

            "QUALITY_COMPLAINT_PQC":
                "Complaint, defect, damage, labeling, or product-quality signals support routing to PQC.",

            "INFO_REQUEST_MI":
                "A medical-information or product-information request supports routing to MI."
        }

        reason = reason_map.get(
            category,
            "The strongest detected domain signal supports this classification."
        )

    return (
        categories,
        round(confidence, 2),
        reason
    )


# ============================================================
# EMAIL FACT EXTRACTION
# ============================================================

def extract_email_facts(request: AnalyzeRequest):

    subject = request.subject or ""
    body = request.body or ""

    combined = f"{subject}\n{body}"

    facts = [
        fact(
            "sender",
            request.sender or NOT_STATED,
            1.0 if request.sender else 0.0,
            "email"
        ),

        fact(
            "subject",
            request.subject or NOT_STATED,
            1.0 if request.subject else 0.0,
            "email"
        ),

        fact(
            "attachments",
            ", ".join(request.attachments)
            if request.attachments
            else NOT_STATED,
            1.0 if request.attachments else 0.0,
            "email"
        )
    ]

    # Patient
    value, confidence = extract_field(
        combined,
        ["Patient", "Patient ID"]
    )

    if value == NOT_STATED:

        value, confidence = regex_extract(
            combined,
            [
                r"\bpatient\s+(?:id\s+)?([A-Z]{1,5}[-\s]?\d{1,8})\b",
                r"\bpatient\s+([A-Z0-9-]{2,20})\b"
            ],
            0.92
        )

    facts.append(
        fact(
            "patient",
            value,
            confidence,
            "email"
        )
    )

    # Reporter
    value, confidence = extract_field(
        combined,
        ["Reporter", "Reporter Name"]
    )

    if value == NOT_STATED:

        value, confidence = regex_extract(
            combined,
            [
                r"\breporter\s*(?:is|:)?\s*(?:Dr\.?\s+)?([A-Z][A-Za-z .'-]{2,50})(?=[.!?,]|$)",
                r"\breported\s+by\s+(?:Dr\.?\s+)?([A-Z][A-Za-z .'-]{2,50})(?=[.!?,]|$)"
            ],
            0.90
        )

    facts.append(
        fact(
            "reporter",
            value,
            confidence,
            "email"
        )
    )

    # Product
    value, confidence = extract_field(
        combined,
        ["Product", "Product Name"]
    )

    if value == NOT_STATED:

        value, confidence = regex_extract(
            combined,
            [
                r"\b(?:received|taking|took|using|used|with|for)\s+(Product\s+[A-Za-z0-9_-]+)",
                r"\b(Product\s+[A-Za-z0-9_-]+)\b"
            ],
            0.92
        )

    facts.append(
        fact(
            "product",
            value,
            confidence,
            "email"
        )
    )

    # Reaction
    value, confidence = extract_field(
        combined,
        ["Reaction", "Adverse Reaction"]
    )

    if value == NOT_STATED:

        value, confidence = regex_extract(
            combined,
            [
                r"\b(?:developed|experienced|reported)\s+([A-Za-z][A-Za-z -]{2,60}?)(?=\.\s|,\s|\.?$)",
                r"\b(?:caused|causing)\s+([A-Za-z][A-Za-z -]{2,60}?)(?=\.\s|,\s|\.?$)"
            ],
            0.86
        )

    facts.append(
        fact(
            "reaction",
            value,
            confidence,
            "email"
        )
    )

    # Severity
    value, confidence = extract_field(
        combined,
        ["Severity"]
    )

    if value == NOT_STATED:

        value, confidence = regex_extract(
            combined,
            [
                r"\bseverity\s+(?:was|is)\s+([A-Za-z-]+)",
                r"\b(severe|serious|non-serious|mild|moderate)\b"
            ],
            0.94
        )

    facts.append(
        fact(
            "severity",
            value,
            confidence,
            "email"
        )
    )

    # Narrative
    value, confidence = extract_field(
        combined,
        [
            "Narrative",
            "Case Narrative",
            "Description"
        ]
    )

    if value == NOT_STATED and body.strip():

        value = clean_value(body)
        confidence = 0.85

    facts.append(
        fact(
            "narrative",
            value,
            confidence,
            "email"
        )
    )

    # Batch
    value, confidence = extract_field(
        combined,
        [
            "Batch",
            "Batch Number"
        ]
    )

    if value == NOT_STATED:

        value, confidence = regex_extract(
            combined,
            [
                r"\bbatch(?:\s+number)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9_-]{2,30})"
            ],
            0.95
        )

    facts.append(
        fact(
            "batch",
            value,
            confidence,
            "email"
        )
    )

    # Lot
    value, confidence = extract_field(
        combined,
        [
            "Lot",
            "Lot Number"
        ]
    )

    if value == NOT_STATED:

        value, confidence = regex_extract(
            combined,
            [
                r"\blot(?:\s+number)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9_-]{2,30})"
            ],
            0.95
        )

    facts.append(
        fact(
            "lot",
            value,
            confidence,
            "email"
        )
    )

    # Issue
    value, confidence = extract_field(
        combined,
        [
            "Issue",
            "Complaint",
            "Quality Issue"
        ]
    )

    if value == NOT_STATED:

        value, confidence = regex_extract(
            combined,
            [
                r"\bcomplaint\s+(?:that|about)\s+(.+?)(?=\.\s|$)",
                r"\bquality issue\s*(?:was|:)?\s*(.+?)(?=\.\s|$)",
                r"\b(defect|defective|damaged|broken|incorrect label|wrong label)\b"
            ],
            0.88
        )

        if value == "broken":
            value = "Product reported as broken"

        elif value in {
            "defect",
            "defective",
            "damaged",
            "incorrect label",
            "wrong label"
        }:
            value = f"Product quality issue: {value}"

    facts.append(
        fact(
            "issue",
            value,
            confidence,
            "email"
        )
    )

    # Photo
    value, confidence = extract_field(
        combined,
        [
            "Photo",
            "Photograph",
            "Image"
        ]
    )

    if value == NOT_STATED:

        photo_terms = [
            "photo attached",
            "photograph attached",
            "image attached",
            "see attached photo",
            "see attached image"
        ]

        if any(
            term in combined.lower()
            for term in photo_terms
        ):
            value = "Photo/image referenced in email"
            confidence = 0.90

    facts.append(
        fact(
            "photo",
            value,
            confidence,
            "email"
        )
    )

    # Question
    value, confidence = extract_field(
        combined,
        [
            "Question",
            "Information Request",
            "Medical Question",
            "Query"
        ]
    )

    if value == NOT_STATED:

        question_match = re.search(
            r"((?:please\s+)?(?:provide|confirm|tell|explain|share)\s+.+?[?.])",
            body,
            re.IGNORECASE
        )

        if question_match:

            value = clean_value(
                question_match.group(1)
            )

            confidence = 0.88

        elif "?" in body:

            question_match = re.search(
                r"([^.!?]+\?)",
                body
            )

            if question_match:

                value = clean_value(
                    question_match.group(1)
                )

                confidence = 0.88

    facts.append(
        fact(
            "question",
            value,
            confidence,
            "email"
        )
    )

    # Topic
    value, confidence = extract_field(
        combined,
        [
            "Topic",
            "Medical Topic"
        ]
    )

    if value == NOT_STATED:

        topic_patterns = [
            r"\b(?:dosage|dose)\b",
            r"\badministration\b",
            r"\bdrug interaction\b",
            r"\bclinical information\b",
            r"\bindications?\b",
            r"\bcontraindication\b"
        ]

        for pattern in topic_patterns:

            match = re.search(
                pattern,
                combined,
                re.IGNORECASE
            )

            if match:

                value = match.group(0)
                confidence = 0.85
                break

    facts.append(
        fact(
            "topic",
            value,
            confidence,
            "email"
        )
    )

    return facts


# ============================================================
# DOCUMENT FACT EXTRACTION
# ============================================================

def extract_document_facts(
    text: str,
    page_number: int,
    filename: str
):

    definitions = [
        ("patient", ["Patient", "Patient ID"]),
        ("reporter", ["Reporter", "Reporter Name"]),
        ("product", ["Product", "Product Name"]),
        ("reaction", ["Reaction", "Adverse Reaction"]),
        ("severity", ["Severity"]),
        ("narrative", ["Narrative", "Case Narrative", "Description"]),
        ("batch", ["Batch", "Batch Number"]),
        ("lot", ["Lot", "Lot Number"]),
        ("issue", ["Issue", "Complaint", "Quality Issue"]),
        ("photo", ["Photo", "Photograph", "Image"]),
        (
            "question",
            [
                "Question",
                "Information Request",
                "Medical Question",
                "Query"
            ]
        ),
        (
            "topic",
            [
                "Topic",
                "Medical Topic"
            ]
        )
    ]

    facts = []

    for field_name, labels in definitions:

        value, confidence = extract_field(
            text,
            labels
        )

        facts.append(
            DocumentFact(
                field=field_name,
                value=value,
                confidence=round(confidence, 2),
                source=f"{filename}:page:{page_number}",
                page_number=page_number
            )
        )

    return facts


# ============================================================
# SUMMARY
# ============================================================

def create_summary(
    filename: str,
    categories: list[str],
    evidence: list[PageEvidence]
):

    usable = [
        e.text.replace("\n", " ").strip()
        for e in evidence
        if e.text != NOT_STATED
    ]

    if not usable:

        return (
            f"{filename} contains no reliably extracted text. "
            "The document may be scanned, image-based, or require OCR/vision processing. "
            "Human review is recommended because reliable text evidence was unavailable."
        )

    category_text = ", ".join(categories)

    content = " ".join(usable)

    if len(content) > 1800:
        content = content[:1800].rstrip() + "..."

    sentences = [
        f"The document analyzed was {filename}.",
        f"The detected category is {category_text}.",
        f"The document contains {len(evidence)} page(s).",
        "Text was extracted directly from the available PDF content.",
        "The extracted evidence was retained with page-level references.",
        f"The available document content includes: {content}.",
        "No information outside the extracted document content was used.",
        "Fields that were not explicitly present were marked as Not stated.",
        "Extracted facts have confidence scores.",
        "The classification decision is based on detected document signals.",
        "Each extracted document fact is linked to its source page.",
        "Documents with insufficient or ambiguous evidence are routed for human review."
    ]

    return " ".join(sentences)


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "ai-service",
        "version": "1.2.0"
    }


@app.get("/")
def root():

    return {
        "service": "Clinevo Smart Inbox AI Service",
        "version": "1.2.0",
        "status": "running"
    }


# ============================================================
# EMAIL ANALYSIS
# ============================================================

@app.post(
    "/analyze",
    response_model=AnalyzeResponse
)
def analyze(request: AnalyzeRequest):

    started = time.perf_counter()

    text = f"{request.subject}\n{request.body}"

    categories, confidence, reason = classify_text(text)

    facts = extract_email_facts(request)

    low_confidence = confidence < 0.85

    multiple_categories = len(categories) > 1

    missing_body = not request.body.strip()

    low_fact_confidence = any(
        item.value != NOT_STATED
        and item.confidence < 0.60
        for item in facts
    )

    human_review_required = (
        low_confidence
        or multiple_categories
        or missing_body
        or low_fact_confidence
    )

    elapsed_ms = max(
        1,
        round(
            (time.perf_counter() - started) * 1000
        )
    )

    return AnalyzeResponse(
        categories=categories,
        classification_confidence=confidence,
        reason=reason,
        facts=facts,
        human_review_required=human_review_required,
        processing_time_ms=elapsed_ms,
        processed_at=utc_now()
    )


# ============================================================
# PDF DOCUMENT ANALYSIS
# ============================================================

@app.post(
    "/analyze-document",
    response_model=DocumentAnalysisResponse
)
async def analyze_document(
    file: UploadFile = File(...)
):

    started = time.perf_counter()

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="PDF filename is required."
        )

    content = await file.read()

    if not content:

        raise HTTPException(
            status_code=400,
            detail="Uploaded PDF is empty."
        )

    try:

        document = fitz.open(
            stream=content,
            filetype="pdf"
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Invalid or unreadable PDF."
        )

    evidence = []
    facts = []

    for index, page in enumerate(document):

        page_number = index + 1

        text = page.get_text("text").strip()

        if text:

            confidence = 0.95

            evidence.append(
                PageEvidence(
                    page_number=page_number,
                    text=text,
                    confidence=confidence,
                    source=f"{file.filename}:page:{page_number}"
                )
            )

            facts.extend(
                extract_document_facts(
                    text,
                    page_number,
                    file.filename
                )
            )

        else:

            evidence.append(
                PageEvidence(
                    page_number=page_number,
                    text=NOT_STATED,
                    confidence=0.20,
                    source=f"{file.filename}:page:{page_number}"
                )
            )

    full_text = "\n".join(
        e.text
        for e in evidence
        if e.text != NOT_STATED
    )

    has_text = bool(full_text.strip())

    document_type = (
        "DIGITAL_TEXT_PDF"
        if has_text
        else "SCANNED_OR_IMAGE_PDF"
    )

    (
        categories,
        classification_confidence,
        classification_reason
    ) = classify_text(full_text)

    populated_low_confidence = any(
        item.value != NOT_STATED
        and item.confidence < 0.85
        for item in facts
    )

    low_evidence = any(
        item.confidence < 0.85
        for item in evidence
    )

    requires_ocr_vision = not has_text

    human_review_required = (
        requires_ocr_vision
        or populated_low_confidence
        or low_evidence
        or len(categories) > 1
    )

    summary = create_summary(
        file.filename,
        categories,
        evidence
    )

    extracted_text = "\n\n".join(
        f"[Page {item.page_number}]\n{item.text}"
        for item in evidence
    )

    elapsed_ms = max(
        1,
        round(
            (time.perf_counter() - started) * 1000
        )
    )

    page_count = len(evidence)

    document.close()

    return DocumentAnalysisResponse(
        filename=file.filename,
        page_count=page_count,
        document_type=document_type,
        extracted_text=extracted_text,
        evidence=evidence,
        facts=facts,
        categories=categories,
        classification_confidence=classification_confidence,
        classification_reason=classification_reason,
        document_summary=summary,
        human_review_required=human_review_required,
        processing_time_ms=elapsed_ms,
        processed_at=utc_now()
    )