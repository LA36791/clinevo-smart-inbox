from datetime import datetime, timezone
import io
import os
import re
import shutil
import time

import pytesseract

# Portable Tesseract discovery: prefer explicit env var, then common Windows
# install locations. Avoids hardcoded Linux-only paths like /usr/bin.
for _candidate in (
    os.environ.get("TESSERACT_CMD"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
):
    if _candidate and os.path.exists(_candidate):
        pytesseract.pytesseract.tesseract_cmd = _candidate
        break
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader
from pdf2image import convert_from_bytes

from models import AnalysisResult, ClassificationDecision, Evidence, ExtractedFact, PageResult
from providers import DeterministicProvider

# Initialize provider (LLM if available, deterministic fallback)
provider = DeterministicProvider()

app = FastAPI(
    title="Clinevo Smart Inbox AI Service",
    version="1.2.0"
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
        "Issue",
        "Topic",
        "Narrative",
    ]

    other_labels = [item for item in labels if item.lower() != label.lower()]
    label_pattern = "|".join(re.escape(item) for item in other_labels)

    pattern = (
        rf"(?<!\w){re.escape(label)}\s*[:\-]\s*"
        rf"(.*?)"
        rf"(?=\s+(?:{label_pattern})(?:\s*[\:\-]|\s)|\n|$)"
    )

    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

    if match:
        value = re.sub(r"\s+", " ", match.group(1)).strip(" :-\n\r\t")
        value = value.split("\n")[0].strip(" :-\n\r\t")
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



MI_QUESTION_SIGNALS = (
    "?",
    "what is",
    "what are",
    "how should",
    "how do",
    "how does",
    "can you",
    "could you",
    "please advise",
    "please confirm",
    "please provide",
    "please share",
    "requesting information",
    "request for information",
    "information request",
    "medical information",
    "drug information",
    "i would like to know",
    "we would like to know",
    "kindly advise",
    "inquiry",
    "enquiry",
)


def is_genuine_question(text: str) -> bool:
    """Only treat content as an MI question when it actually asks something."""
    normalized = (text or "").lower()
    if "?" in normalized:
        return True
    return any(sig in normalized for sig in MI_QUESTION_SIGNALS)


def detect_language_flag(text: str) -> str:
    """Cheap language signal: non-ASCII ratio + common non-English markers."""
    sample = (text or "")[:2000]
    if not sample.strip():
        return "unknown"
    non_ascii = sum(1 for ch in sample if ord(ch) > 127)
    if non_ascii / max(len(sample), 1) > 0.15:
        return "non-en"
    markers = (
        " der ", " die ", " das ", " und ", "_patient", " effet ",
        " effets ", " r\u00e9action ", " r\u00e9actions ", " s\u00e9v\u00e9rit\u00e9 ",
        " signal\u00e9 ", " m\u00e9dicament ", " notifica ", " reacci\u00f3n ",
        " gravedad ", " informe ", " paciente ", " meldung ", " unerw\u00fcnscht ",
    )
    low = sample.lower()
    if any(m.strip() and m.strip() in low for m in markers):
        return "non-en"
    return "en"


def extract_table_rows(text: str, max_rows: int = 20):
    """Best-effort structured-table extraction (pipe / multi-space / tab rows)."""
    rows = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if "|" in s:
            cells = [c.strip() for c in s.strip().strip("|").split("|")]
        elif "\t" in line:
            cells = [c.strip() for c in line.split("\t")]
        elif re.search(r"\s{2,}", s):
            cells = [c.strip() for c in re.split(r"\s{2,}", s)]
        else:
            continue
        cells = [c for c in cells if c]
        if len(cells) >= 2:
            rows.append(cells)
        if len(rows) >= max_rows:
            break
    return rows


def detect_image_references(text: str, image_count: int = 0):
    """Detect photo/image references; never invent image findings."""
    normalized = (text or "").lower()
    terms = (
        "photo", "photograph", "picture attached", "image attached",
        "photo attached", "see image", "see figure", "as shown in",
        "figure 1", "figure 2", "fig. 1", "fig. 2", "attached image",
    )
    found = sorted({term for term in terms if term in normalized})
    return found, image_count


def reorder_multicolumn_lines(text: str) -> str:
    """Light multi-column repair: split very wide double-gap lines.

    Only merges lines that look like two columns side-by-side; normal
    single-column text passes through unchanged.
    """
    lines = (text or "").splitlines()
    if not lines:
        return text
    wide = [ln for ln in lines if re.search(r"\S\s{3,}\S", ln) and len(ln) > 60]
    if len(wide) < 3:
        return text
    left, right = [], []
    for ln in lines:
        parts = re.split(r"\s{3,}", ln.rstrip(), maxsplit=1)
        if len(parts) == 2 and len(parts[0]) > 10 and len(parts[1]) > 10:
            left.append(parts[0].rstrip())
            right.append(parts[1].lstrip())
        else:
            left.append(ln)
    if not right:
        return text
    return "\n".join(left + ["", "[Right column continuation]"] + right)


def snip(text: str, limit: int = 500) -> str:
    s = re.sub(r"\s+", " ", text or "").strip()
    return s[:limit]


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
    reporter = extract_value(text, "Reporter")
    issue = extract_value(text, "Issue")
    topic = extract_value(text, "Topic")
    narrative = extract_value(text, "Narrative")

    photo_terms = ("photo", "photograph", "image attached", "picture attached")
    photo_mentioned = (
        "Yes" if any(t in normalized for t in photo_terms) else "Not stated"
    )

    # Non-English content detection: retains the original text as evidence and
    # routes the document to human review rather than attempting translation.
    sample = text[:2000]
    non_ascii_ratio = (
        sum(1 for ch in sample if ord(ch) > 127) / max(len(sample), 1)
    )
    non_english = non_ascii_ratio > 0.15

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
        extract_fact(
            "reporter",
            reporter,
            source_type,
            source_id,
            text,
            page,
            extraction_confidence,
        ),
        extract_fact(
            "narrative",
            narrative,
            source_type,
            source_id,
            text,
            page,
            extraction_confidence,
        ),
        extract_fact(
            "issue",
            issue,
            source_type,
            source_id,
            text,
            page,
            extraction_confidence,
        ),
        extract_fact(
            "photo_mentioned",
            photo_mentioned,
            source_type,
            source_id,
            text,
            page,
            extraction_confidence,
        ),
        extract_fact(
            "mi_topic",
            topic,
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
        "dosage",
        "indication",
        "contraindication",
        "advise",
        "store",
        "storage",
        "administration",
        "interaction",
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

    if scores.get('INFO_REQUEST_MI', 0) > 0 and not is_genuine_question(text):
        scores['INFO_REQUEST_MI'] = 0
        if max(scores.values()) == 0:
            scores['NOT_RELEVANT'] = 1.0
        max_score = max(scores.values())

    # Boost MI when a genuine question is present and MI indicators exist.
    # This prevents "patient" in question context (e.g., "in elderly patients")
    # from incorrectly dominating as a safety report.
    if scores.get('INFO_REQUEST_MI', 0) > 0 and is_genuine_question(text):
        scores['INFO_REQUEST_MI'] += 2
        max_score = max(scores.values())
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

    # Sort categories by confidence descending so the highest-confidence
    # category is primary (first in the list).
    categories.sort(key=lambda c: c.confidence, reverse=True)

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

    _safety_fields = {'patient_id': patient, 'reporter': reporter, 'product': product, 'reaction': reaction, 'severity': severity, 'narrative': narrative}
    _missing_safety = sorted([k for k, v in _safety_fields.items() if v == 'Not stated'])
    _safety_on = any(c.category == 'SAFETY_REPORT_ICSR' for c in categories)
    _low_safety_conf = any(f.confidence < 0.70 and f.value != 'Not stated' for f in facts if f.field in ('patient_id', 'reporter', 'product', 'reaction', 'severity', 'narrative', 'batch'))
    _table_rows = extract_table_rows(text)
    _img_terms, _ = detect_image_references(text, 0)
    _lang = detect_language_flag(text)
    _lang_note = ' Possible non-English content detected; original text preserved without translation.' if _lang != 'en' else ''
    _tbl_note = (' Structured table-like rows detected (%d rows).' % len(_table_rows)) if _table_rows else ''
    _img_note = (' Image/photo reference detected (%s); image content was not interpreted.' % ', '.join(_img_terms[:3])) if _img_terms else ''
    human_review_required = (
        extraction_confidence < 0.75
        or non_english
        or _lang != 'en'
        or bool(_img_terms)
        or (_safety_on and bool(_missing_safety))
        or (_safety_on and _low_safety_conf)
        or any(
            fact.confidence < 0.75 and fact.value != 'Not stated'
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
        f"The reporter is {reporter}. "
        f"The reported quality issue is {issue}. "
        f"A photo is mentioned: {photo_mentioned}. "
        f"The medical-information topic is {topic}. "
        "Facts are retained with source evidence for human verification. "
        + (
            "The document content does not appear to be in English. The original "
            "text is retained as evidence and human review with translation is required. "
            if non_english
            else ""
        )
        + "The system does not infer missing values and uses Not stated when information is unavailable. "
        "Low-confidence or potentially multi-category cases are routed for human review. "
        "The result can therefore be reviewed before any downstream action is taken."
        + _tbl_note + _img_note + _lang_note
    )
    _table_fact_value = ("%d structured rows detected" % len(_table_rows)) if _table_rows else "Not stated"
    _table_fact_ev = "; ".join([" | ".join(r[:6]) for r in _table_rows[:3]]) if _table_rows else text
    facts = list(facts) + [
        extract_fact("table_rows", _table_fact_value, source_type, source_id, _table_fact_ev, page, 0.80 if _table_rows else 0.0),
        extract_fact("image_reference", ("Image/photo reference detected: " + ", ".join(_img_terms[:4])) if _img_terms else "Not stated", source_type, source_id, text, page, 0.80 if _img_terms else 0.0),
    ]

    elapsed = int((time.perf_counter() - start) * 1000)

    return AnalysisResult(
        document_type="DOCUMENT",
        categories=categories,
        facts=facts,
        summary=summary,
        human_review_required=human_review_required,
        processing_time_ms=elapsed,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        page_count=1,
        extracted_text=text,
        pages=[PageResult(page=page or 1, text=text, confidence=extraction_confidence, source=source_type)],
        ocr_confidence=None,
        language_flag=_lang,
    )


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "clinevo-smart-inbox-ai",
        "version": "1.2.0",
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
            repaired = reorder_multicolumn_lines(combined_text)
            result = analyze_text(
                repaired,
                filename,
                source_type="PDF",
                page=1,
                extraction_confidence=0.95,
            )

            # Map fact evidence to the actual page where the value appears.
            for fact in result.facts:
                fact_value = str(fact.value).strip().lower()
                if fact_value and fact_value != "not stated":
                    for page_number, page_text in enumerate(page_texts, start=1):
                        if page_text and fact_value in page_text.lower():
                            for ev in fact.evidence:
                                ev.page = page_number
                            break

            result.document_type = "DIGITAL_TEXT_PDF"
            result.page_count = len(page_texts)
            result.extracted_text = combined_text
            result.pages = [
                PageResult(page=i + 1, text=tx, confidence=0.95, source="PDF")
                for i, tx in enumerate(page_texts)
            ]
            result.ocr_confidence = None
            result.language_flag = detect_language_flag(combined_text)
            if result.language_flag != "en":
                result.human_review_required = True
            result.processing_time_ms = int(
                (time.perf_counter() - start) * 1000
            )

            return result

    except Exception:
        pass

    # Fallback: render scanned PDF pages and perform OCR.
    try:
        # Windows: pdf2image finds poppler on PATH when poppler_path is None;
        # the previous hardcoded "/usr/bin" only worked on Linux.
        poppler_path = shutil.which("pdfinfo")
        poppler_path = (
            os.path.dirname(poppler_path) if poppler_path else None
        )
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
                page_count=len(images),
                extracted_text="",
                pages=[
                    PageResult(page=n, text=tx, confidence=cf, source="PDF_OCR")
                    for n, tx, cf in ocr_pages
                ],
                ocr_confidence=round(overall_confidence, 4),
                language_flag="unknown",
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
        result.page_count = len(images)
        result.extracted_text = combined_ocr
        result.pages = [
            PageResult(page=n, text=tx, confidence=cf, source="PDF_OCR")
            for n, tx, cf in ocr_pages
        ]
        result.ocr_confidence = round(overall_confidence, 4)
        result.language_flag = detect_language_flag(combined_ocr)
        if result.language_flag != "en":
            result.human_review_required = True

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
            page_count=len(images) if "images" in dir() else 0,
            extracted_text="",
            pages=[],
            ocr_confidence=0.0,
            language_flag="unknown",
        )





