from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    source_type: str
    source_id: str
    page: Optional[int] = None
    text: str
    confidence: float = Field(ge=0, le=1)

class ExtractedFact(BaseModel):
    field: str
    value: Any = "Not stated"
    confidence: float = Field(ge=0, le=1)
    evidence: List[Evidence] = []

class ClassificationDecision(BaseModel):
    category: str
    confidence: float = Field(ge=0, le=1)
    reason: str
    evidence: List[Evidence] = []

class AnalysisResult(BaseModel):
    document_type: str
    categories: List[ClassificationDecision]
    facts: List[ExtractedFact]
    summary: str
    human_review_required: bool
    processing_time_ms: int
    timestamp_utc: str
    page_count: int = 0
    extracted_text: str = ''
    pages: list = []
    ocr_confidence: float | None = None
    language_flag: str = 'en'
    evidence_summary: Optional[Dict[str, Any]] = None

from pydantic import BaseModel as _BM2


class PageResult(_BM2):
    page: int
    text: str
    confidence: float = 0.95
    source: str = 'PDF_TEXT'
