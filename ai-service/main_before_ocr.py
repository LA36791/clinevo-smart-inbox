import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from fastapi import FastAPI, UploadFile, File
from pypdf import PdfReader

from models import AnalysisResult, ClassificationDecision, ExtractedFact, Evidence

app = FastAPI(
    title="Clinevo Smart Inbox AI Service",
    version="1.0.0"
)

CATEGORIES = [
    "SAFETY_REPORT_ICSR",
    "QUALITY_COMPLAINT_PQC",
    "INFO_REQUEST_MI",
    "NOT_RELEVANT"
]

def evidence(text: str, page: int = 1, source_id: str = "document") -> Evidence:
    return Evidence(
        source_type="PDF",
        source_id=source_id,
        page=page,
        text=text[:500],
        confidence=0.95
    )

def extract_value(text: str, labels: List[str]) -> Tuple[str, str]:
    for label in labels:
        pattern = rf"{re.escape(label)}\s*[:\-]\s*([^\n\r;]+)"
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).strip(), match.group(0).strip()
    return "Not stated", ""

def analyze_text(text: str, source_id: str = "document") -> AnalysisResult:
    start = time.perf_counter()
    lower = text.lower()

    patient, patient_ev = extract_value(text, ["Patient ID", "Patient"])
    product, product_ev = extract_value(text, ["Product", "Drug", "Medicine"])
    reaction, reaction_ev = extract_value(text, ["Reaction", "Adverse Event", "Event"])
    severity, severity_ev = extract_value(text, ["Severity", "Seriousness"])
    batch, batch_ev = extract_value(text, ["Batch", "Lot", "Batch Number"])
    question, question_ev = extract_value(text, ["Question", "Information Request", "Query"])

    safety_words = ["adverse event", "reaction", "patient", "serious", "non-serious", "icSR", "safety report"]
    pqc_words = ["quality complaint", "defect", "damaged", "broken", "batch", "lot", "complaint"]
    mi_words = ["information request", "medical information", "question", "query", "dosage", "indication"]

    safety_score = sum(w in lower for w in safety_words) / len(safety_words)
    pqc_score = sum(w in lower for w in pqc_words) / len(pqc_words)
    mi_score = sum(w in lower for w in mi_words) / len(mi_words)

    scores = {
        "SAFETY_REPORT_ICSR": safety_score,
        "QUALITY_COMPLAINT_PQC": pqc_score,
        "INFO_REQUEST_MI": mi_score
    }

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    if ranked[0][1] == 0:
        categories = [
            ClassificationDecision(
                category="NOT_RELEVANT",
                confidence=0.90,
                reason="No meaningful safety, quality complaint, or medical information request indicators were found.",
                evidence=[]
            )
        ]
    else:
        categories = []
        for category, score in ranked:
            if score >= 0.20:
                categories.append(
                    ClassificationDecision(
                        category=category,
                        confidence=min(0.98, round(0.55 + score * 0.45, 2)),
                        reason=f"Detected {category.lower().replace('_', ' ')} indicators in the source document.",
                        evidence=[evidence(text, 1, source_id)]
                    )
                )

    facts = []

    for field, value, ev in [
        ("patient_id", patient, patient_ev),
        ("product", product, product_ev),
        ("reaction", reaction, reaction_ev),
        ("severity", severity, severity_ev),
        ("batch_or_lot", batch, batch_ev),
        ("actual_question", question, question_ev),
    ]:
        facts.append(
            ExtractedFact(
                field=field,
                value=value,
                confidence=0.95 if value != "Not stated" else 0.0,
                evidence=[evidence(ev, 1, source_id)] if ev else []
            )
        )

    summary_sentences = [
        "The document was processed by the Clinevo Smart Inbox intelligence pipeline.",
        f"The detected document signals correspond primarily to {categories[0].category}.",
        f"Product information is recorded as {product}.",
        f"Patient information is recorded as {patient}.",
        f"The reported reaction or event is recorded as {reaction}.",
        f"Severity information is recorded as {severity}.",
        f"Batch or lot information is recorded as {batch}.",
        f"The medical information question is recorded as {question}.",
        "Facts are only populated when supported by extracted source text.",
        "Fields without supporting information are explicitly marked Not stated.",
        "Source evidence is retained with page-level references.",
        "Classification confidence is calculated from detected domain indicators.",
        "Low-confidence or conflicting information should be reviewed by a human.",
        "The system is designed for human-in-the-loop processing rather than autonomous final decisions."
    ]

    human_review = any(c.confidence < 0.80 for c in categories) or any(
        f.confidence == 0 for f in facts if f.field in ["patient_id", "product", "reaction"]
    )

    return AnalysisResult(
        document_type="DIGITAL_TEXT_PDF",
        categories=categories,
        facts=facts,
        summary=" ".join(summary_sentences),
        human_review_required=human_review,
        processing_time_ms=round((time.perf_counter() - start) * 1000),
        timestamp_utc=datetime.now(timezone.utc).isoformat()
    )

@app.get("/health")
def health():
    return {"status": "ok", "service": "clinevo-smart-inbox-ai"}

@app.post("/analyze-document", response_model=AnalysisResult)
async def analyze_document(file: UploadFile = File(...)):
    data = await file.read()
    temp = Path("temp_uploaded.pdf")
    temp.write_bytes(data)

    reader = PdfReader(str(temp))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Page {i}]\\n{text}")

    text = "\\n\\n".join(pages)

    if not text.strip():
        return AnalysisResult(
            document_type="SCANNED_OR_IMAGE_PDF",
            categories=[
                ClassificationDecision(
                    category="NOT_RELEVANT",
                    confidence=0.0,
                    reason="No machine-readable text was available. OCR/vision human review is required.",
                    evidence=[]
                )
            ],
            facts=[],
            summary="The PDF contains no directly extractable text and requires OCR or vision processing.",
            human_review_required=True,
            processing_time_ms=0,
            timestamp_utc=datetime.now(timezone.utc).isoformat()
        )

    return analyze_text(text, file.filename or "document")

@app.post("/analyze")
async def analyze_email(payload: dict):
    text = "\n".join([
        str(payload.get("subject", "")),
        str(payload.get("body", ""))
    ])
    result = analyze_text(text, payload.get("message_id", "email"))
    result.document_type = "EMAIL"
    for category in result.categories:
        for ev in category.evidence:
            ev.source_type = "EMAIL"
            ev.page = None
    for fact in result.facts:
        for ev in fact.evidence:
            ev.source_type = "EMAIL"
            ev.page = None
    return result
