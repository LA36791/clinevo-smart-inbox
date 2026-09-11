from datetime import datetime, timezone
import io
import re
import time

import pytesseract
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from pdf2image import convert_from_bytes

from models import AnalysisResult, ClassificationDecision, Evidence, ExtractedFact

pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

app = FastAPI(
    title="Clinevo Smart Inbox AI Service",
    version="1.1.0"
)

CATEGORIES = [
    "SAFETY_REPORT_ICSR",
    "QUALITY_COMPLAINT_PQC",
    "INFO_REQUEST_MI",
    "NOT_RELEVANT",
]


def evidence(source_type: str, source_id: str, text: str, page=None, confidence=0.95):
    return Evidence(
        source_type=source_type,
        source_id=source_id,
        page=page,
        text=text.strip(),
        confidence=max(0.0, min(1.0, confidence)),
    )


def extract_value(text: str, label: str):
    labels = [
        "Patient ID",
        "Patient",
        "Reporter",
        "Product",
        "Reaction",
        "Severity",
        "Batch",
        "Lot",
        "Question",
        "Actual Question",
    ]

    other_labels = [item for item in labels if item.lower() != label.lower()]
    label_pattern = "|".join(re.escape(item) for item in other_labels)

    pattern = (
        rf"(?<!\w){re.escape(label)}\s*[:\-]?\s*"
        rf"(.*?)"
        rf"(?=\s+(?:{label_pattern})(?:\s*[:\-]|\s)|$)"
    )

    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    if match:
        value = re.sub(r"\s+", " ", match.group(1)).strip(" :-")
        return value if value else "Not stated"

    return "Not stated"


def extract_fact(
    field: str,
    value: str,
    source_type: str,
    source_id: str,
    source_text: str,
    page=None,
    confidence=0.95,
):
    if value == "Not stated":
        return ExtractedFact(
            field=field,
            value=value,
            confidence=0.0,
            evidence=[],
        )

    return ExtractedFact(
        field=field,
        value=value,
        confidence=confidence,
        evidence=[
            evidence(
                source_type,
                source_id,
                source_text,
                page,
                confidence,
            )
        ],
    )


def analyze_text(
    text: str,
    source_id: str,
    source_type: str = "EMAIL",
    page=None,
    extraction_confidence=0.95,
):
    start = time.perf_counter()

    normalized = text.lower()

    patient = extract_value(text, "Patient")
    if patient == "Not stated":
        patient = extract_value(text, "Patient ID")
    product = extract_value(text, "Product")
    reaction = extract_value(text, "Reaction")
    severity = extract_value(text, "Severity")
    batch = extract_value(text, "Batch")
    question = extract_value(text, "Question")

    facts = [
        extract_fact(
            "patient_id",
            patient,
            source_type,
            source_id,
            text,
            page,
            extraction_confidence,
        ),
        extract_fact(
            "product",
            product,
            source_type,
            source_id,
            text,
            page,
            extraction_confidence,
        ),
        extract_fact(
            "reaction",
            reaction,
            source_type,
            source_id,
            text,
            page,
            extraction_confidence,
        ),
        extract_fact(
            "severity",
            severity,
            source_type,
            source_id,
            text,
            page,
            extraction_confidence,
        ),
        extract_fact(
            "batch",
            batch,
            source_type,
            source_id,
            text,
            page,
            extraction_confidence,
        ),
        extract_fact(
            "actual_question",
            question,
            source_type,
            source_id,
            text,
            page,
            extraction_confidence,
        ),
    ]

    scores = {
        "SAFETY_REPORT_ICSR": 0.0,
        "QUALITY_COMPLAINT_PQC": 0.0,
        "INFO_REQUEST_MI": 0.0,
        "NOT_RELEVANT": 0.0,
    }

    safety_terms = [
        "safety report",
        "adverse event",
        "adverse reaction",
        "reaction",
        "patient",
        "severity",
        "serious",
        "non-serious",
    ]

    pqc_terms = [
        "quality complaint",
        "complaint",
        "product defect",
        "defective",
        "damaged",
        "broken",
        "leak",
        "leaking",
        "missing tablet",
        "packaging defect",
        "wrong label",
    ]

    mi_terms = [
        "information request",
        "medical information",
        "question",
        "asking",
        "inquiry",
        "dose",
        "dosing",
        "indication",
        "contraindication",
    ]

    for term in safety_terms:
        if term in normalized:
            scores["SAFETY_REPORT_ICSR"] += 1

    for term in pqc_terms:
        if term in normalized:
            scores["QUALITY_COMPLAINT_PQC"] += 1

    for term in mi_terms:
        if term in normalized:
            scores["INFO_REQUEST_MI"] += 1

    if max(scores.values()) == 0:
        scores["NOT_RELEVANT"] = 1.0

    max_score = max(scores.values())
    categories = []

    for category, score in scores.items():
        if score <= 0:
            continue

        confidence = min(
            0.99,
            0.60 + (score / max(max_score, 1)) * 0.30,
        )

        if category == "SAFETY_REPORT_ICSR":
            reason = "Safety/adverse-event indicators were detected."
        elif category == "QUALITY_COMPLAINT_PQC":
            reason = "Product quality/complaint indicators were detected."
        elif category == "INFO_REQUEST_MI":
            reason = "A medical-information or product-information request was detected."
        else:
            reason = "No relevant safety, quality, or information-request indicators were detected."

        categories.append(
            ClassificationDecision(
                category=category,
                confidence=confidence,
                reason=reason,
                evidence=[
                    evidence(
                        source_type,
                        source_id,
                        text,
                        page,
                        extraction_confidence,
                    )
                ],
            )
        )

    # Allow multiple relevant buckets when evidence supports them.
    for category, score in scores.items():
        if category == "NOT_RELEVANT" or score <= 0:
            continue

        if not any(c.category == category for c in categories):
            categories.append(
                ClassificationDecision(
                    category=category,
                    confidence=0.60,
                    reason="Relevant indicators were detected.",
                    evidence=[
                        evidence(
                            source_type,
                            source_id,
                            text,
                            page,
                            extraction_confidence,
                        )
                    ],
                )
            )

    human_review_required = (
        extraction_confidence < 0.75
        or any(
            fact.confidence < 0.75
            for fact in facts
        )
        or len(categories) > 1
    )

    summary = (
        "The document was processed by the Clinevo Smart Inbox AI service. "
        "The system identified the document as requiring domain classification. "
        f"The strongest detected category is {categories[0].category if categories else 'NOT_RELEVANT'}. "
        f"The classification confidence is {categories[0].confidence:.2f} if a category was detected. "
        f"The patient identifier is {patient}. "
        f"The reported product is {product}. "
        f"The reported reaction is {reaction}. "
        f"The reported severity is {severity}. "
        f"The reported batch or lot is {batch}. "
        f"The extracted question is {question}. "
        "Facts are retained with source evidence for human verification. "
        "The system does not infer missing values and uses Not stated when information is unavailable. "
        "Low-confidence or potentially multi-category cases are routed for human review. "
        "The result can therefore be reviewed before any downstream action is taken."
    )

    elapsed = int((time.perf_counter() - start) * 1000)

    return AnalysisResult(
        document_type="DOCUMENT",
        categories=categories,
        facts=facts,
        summary=summary,
        human_review_required=human_review_required,
        processing_time_ms=elapsed,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "clinevo-smart-inbox-ai",
        "version": "1.1.0",
    }


@app.post("/analyze")
async def analyze_email(payload: dict):
    text = "\n".join(
        [
            str(payload.get("subject", "")),
            str(payload.get("body", "")),
        ]
    )

    result = analyze_text(
        text,
        payload.get("message_id", "email"),
        source_type="EMAIL",
        page=None,
        extraction_confidence=0.95,
    )

    result.document_type = "EMAIL"

    return result


@app.post("/analyze-document")
async def analyze_document(file: UploadFile = File(...)):
    start = time.perf_counter()

    content = await file.read()
    filename = file.filename or "uploaded.pdf"

    # First attempt: direct digital-PDF extraction.
    try:
        reader = PdfReader(io.BytesIO(content))
        page_texts = []

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            page_texts.append(page_text.strip())

        combined_text = "\n".join(
            f"[Page {i}] {text}"
            for i, text in enumerate(page_texts, start=1)
            if text
        )

        if combined_text.strip():
            result = analyze_text(
                combined_text,
                filename,
                source_type="PDF",
                page=1,
                extraction_confidence=0.95,
            )

            result.document_type = "DIGITAL_TEXT_PDF"
            result.processing_time_ms = int(
                (time.perf_counter() - start) * 1000
            )

            return result

    except Exception:
        pass

    # Fallback: render scanned PDF pages and perform OCR.
    try:
        poppler_path = "/usr/bin"
        images = convert_from_bytes(
            content,
            dpi=200,
            fmt="png",
            poppler_path=poppler_path,
        )

        ocr_pages = []
        page_confidences = []

        for page_number, image in enumerate(images, start=1):
            data = pytesseract.image_to_data(
                image,
                output_type=pytesseract.Output.DICT,
            )

            words = []
            confidences = []

            for i, word in enumerate(data["text"]):
                word = word.strip()

                if not word:
                    continue

                words.append(word)

                try:
                    confidence = float(data["conf"][i])
                    if confidence >= 0:
                        confidences.append(confidence / 100.0)
                except (ValueError, TypeError):
                    pass

            page_text = " ".join(words).strip()

            if page_text:
                page_confidence = (
                    sum(confidences) / len(confidences)
                    if confidences
                    else 0.50
                )
            else:
                page_confidence = 0.0

            ocr_pages.append(
                (page_number, page_text, page_confidence)
            )
            page_confidences.append(page_confidence)

        combined_ocr = "\n".join(
            f"[Page {page}] {text}"
            for page, text, _ in ocr_pages
            if text
        )

        overall_confidence = (
            sum(page_confidences) / len(page_confidences)
            if page_confidences
            else 0.0
        )

        if not combined_ocr.strip():
            return AnalysisResult(
                document_type="SCANNED_OR_IMAGE_PDF",
                categories=[
                    ClassificationDecision(
                        category="NOT_RELEVANT",
                        confidence=0.0,
                        reason="No usable text could be extracted from the scanned document.",
                        evidence=[],
                    )
                ],
                facts=[],
                summary=(
                    "The PDF did not contain directly extractable text and OCR did not "
                    "produce usable content. Human review is required."
                ),
                human_review_required=True,
                processing_time_ms=int(
                    (time.perf_counter() - start) * 1000
                ),
                timestamp_utc=datetime.now(timezone.utc).isoformat(),
            )

        result = analyze_text(
            combined_ocr,
            filename,
            source_type="PDF_OCR",
            page=None,
            extraction_confidence=overall_confidence,
        )

        # Make OCR uncertainty and page-level traceability visible.
        result.document_type = "SCANNED_OCR_PDF"

        for category in result.categories:
            for ev in category.evidence:
                ev.confidence = overall_confidence
                for page_number, page_text, _ in ocr_pages:
                    if page_text and ev.text.replace("[Page 1] ", "").strip() in page_text:
                        ev.page = page_number
                        break

        for fact in result.facts:
            for ev in fact.evidence:
                ev.confidence = overall_confidence

                # Preserve exact PDF page traceability for OCR evidence.
                # For a single-page OCR PDF, every extracted fact evidence
                # item belongs to page 1.
                if len(ocr_pages) == 1 and ocr_pages[0][1]:
                    ev.page = ocr_pages[0][0]
                else:
                    fact_value = str(fact.value).strip()

                    if fact_value and fact_value != "Not stated":
                        for page_number, page_text, _ in ocr_pages:
                            if page_text and fact_value.lower() in page_text.lower():
                                ev.page = page_number
                                break
            fact.confidence = min(
                fact.confidence,
                overall_confidence,
            )

        result.human_review_required = (
            True if overall_confidence < 0.85
            else result.human_review_required
        )

        result.summary += (
            f" OCR was used because direct PDF text extraction was unavailable. "
            f"The average OCR confidence was {overall_confidence:.2f}."
        )

        result.processing_time_ms = int(
            (time.perf_counter() - start) * 1000
        )

        return result

    except Exception as exc:
        return AnalysisResult(
            document_type="SCANNED_OR_IMAGE_PDF",
            categories=[
                ClassificationDecision(
                    category="NOT_RELEVANT",
                    confidence=0.0,
                    reason=f"OCR processing failed: {type(exc).__name__}.",
                    evidence=[],
                )
            ],
            facts=[],
            summary=(
                "The document could not be processed successfully. "
                "Human review is required."
            ),
            human_review_required=True,
            processing_time_ms=int(
                (time.perf_counter() - start) * 1000
            ),
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )





