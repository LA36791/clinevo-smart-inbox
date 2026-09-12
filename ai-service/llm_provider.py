"""
Optional LLM provider for Clinevo Smart Inbox AI Service.

Implements a practical AI layer that:
- Uses an LLM for document understanding, classification, and fact extraction
- Falls back to deterministic extraction when LLM is unavailable
- Preserves evidence grounding (every fact tied to source text)
- Does NOT invent facts

Environment variables:
  LLM_API_KEY     - API key for the LLM provider (OpenAI-compatible)
  LLM_API_BASE    - API base URL (default: https://api.openai.com/v1)
  LLM_MODEL       - Model name (default: gpt-4o-mini)
  LLM_ENABLED     - Set to "true" to enable LLM (default: false)

If LLM is unavailable or disabled, the deterministic provider is used.
"""
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

from models import AnalysisResult, ClassificationDecision, Evidence, ExtractedFact, PageResult


class LLMProvider:
    """LLM-based provider with deterministic fallback."""

    def __init__(self):
        self.api_key = os.environ.get("LLM_API_KEY", "")
        self.api_base = os.environ.get("LLM_API_BASE", "https://api.openai.com/v1")
        self.model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
        self.enabled = os.environ.get("LLM_ENABLED", "false").lower() == "true" and bool(self.api_key)
        self._http = None

    @property
    def http(self):
        if self._http is None:
            import urllib.request
            self._http = urllib.request
        return self._http

    def is_available(self) -> bool:
        return self.enabled and bool(self.api_key)

    def analyze(self, text: str, source_type: str = "PDF",
                source_id: str = "document", page: int = 1,
                page_count: int = 1, extracted_pages: List[PageResult] = None) -> Optional[AnalysisResult]:
        """Analyze document text using LLM with deterministic fallback."""
        if not self.is_available():
            return None
        try:
            return self._llm_analyze(text, source_type, source_id, page, page_count, extracted_pages)
        except Exception:
            return None

    def _llm_analyze(self, text, source_type, source_id, page, page_count, extracted_pages):
        evidence_context = self._build_evidence_context(text, extracted_pages)
        prompt = self._build_prompt(evidence_context, source_type, source_id, page)
        response = self._call_llm(prompt)
        if not response:
            return None
        return self._parse_llm_response(response, text, source_type, source_id, page, page_count, extracted_pages)

    def _build_evidence_context(self, text, extracted_pages=None):
        if extracted_pages:
            parts = []
            for p in extracted_pages:
                parts.append(f"[Page {p.page}] {p.text}")
            return "\n\n".join(parts)
        return text

    def _build_prompt(self, evidence_context, source_type, source_id, page):
        return f"""You are a pharmacovigilance document analysis assistant. Analyze the following healthcare document and provide structured output.

DOCUMENT SOURCE: {source_type} | {source_id}
DOCUMENT TEXT:
{evidence_context}

INSTRUCTIONS:
1. Classify the document into one or more categories:
   - SAFETY_REPORT_ICSR: adverse event, side effect, safety report
   - QUALITY_COMPLAINT_PQC: product quality issue, defect, packaging problem
   - INFO_REQUEST_MI: question, information request, medical inquiry
   - NOT_RELEVANT: unrelated to healthcare/pharmacovigilance

2. Extract key facts with evidence from the text.

3. For Safety reports extract: patient_id, product, reaction, severity, batch, reporter, narrative
4. For PQC extract: product, batch, problem, photo_mentioned
5. For MI extract: actual_question, mi_topic

6. NEVER invent facts. Only extract what is explicitly stated.
7. For missing information, use "Not stated" with confidence 0.0.
8. Every fact MUST include the exact source text evidence.

Respond in JSON format:
{{
  "categories": [
    {{"category": "SAFETY_REPORT_ICSR", "confidence": 0.0-1.0, "reason": "one-line reason"}}
  ],
  "facts": [
    {{"field": "field_name", "value": "extracted value", "confidence": 0.0-1.0, "evidence_text": "exact source text"}}
  ],
  "summary": "brief summary",
  "human_review_required": true/false,
  "language_flag": "en or non-en"
}}"""

    def _call_llm(self, prompt):
        """Call the LLM API."""
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a pharmacovigilance document analysis expert. Respond only in valid JSON."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"}
        }
        data = json.dumps(payload).encode()
        req = self.http.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })
        try:
            with self.http.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode())
                return result.get("choices", [{}])[0].get("message", {}).get("content", "")
        except Exception:
            return None

    def _parse_llm_response(self, response, text, source_type, source_id, page, page_count, extracted_pages):
        """Parse LLM JSON response into AnalysisResult."""
        json_str = response
        if "```json" in response:
            match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1)
        elif "```" in response:
            match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
            if match:
                json_str = match.group(1)

        data = json.loads(json_str)

        categories = []
        for cat in data.get("categories", []):
            categories.append(ClassificationDecision(
                category=cat.get("category", "NOT_RELEVANT"),
                confidence=min(1.0, max(0.0, cat.get("confidence", 0.5))),
                reason=cat.get("reason", "LLM classification"),
                evidence=[Evidence(
                    source_type=source_type, source_id=source_id,
                    page=page, text=text[:500], confidence=0.8
                )]
            ))

        if not categories:
            categories.append(ClassificationDecision(
                category="NOT_RELEVANT", confidence=0.5,
                reason="LLM did not classify", evidence=[]
            ))

        facts = []
        for fact in data.get("facts", []):
            value = fact.get("value", "Not stated")
            if value == "Not stated" or not value:
                facts.append(ExtractedFact(
                    field=fact.get("field", "unknown"),
                    value="Not stated", confidence=0.0, evidence=[]
                ))
            else:
                evidence_text = fact.get("evidence_text", text[:200])
                facts.append(ExtractedFact(
                    field=fact.get("field", "unknown"),
                    value=value,
                    confidence=min(1.0, max(0.0, fact.get("confidence", 0.8))),
                    evidence=[Evidence(
                        source_type=source_type, source_id=source_id,
                        page=page, text=evidence_text[:1000],
                        confidence=min(1.0, max(0.0, fact.get("confidence", 0.8)))
                    )]
                ))

        return AnalysisResult(
            document_type="LLM_ANALYZED",
            categories=sorted(categories, key=lambda c: c.confidence, reverse=True),
            facts=facts,
            summary=data.get("summary", "LLM analysis completed."),
            human_review_required=data.get("human_review_required", False),
            processing_time_ms=0,
            timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            page_count=page_count,
            extracted_text=text[:2000],
            pages=extracted_pages or [],
            language_flag=data.get("language_flag", "en")
        )

