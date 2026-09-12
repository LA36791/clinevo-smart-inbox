"""
Evidence Engine for CLINEVO EvidenceOS.

Implements:
- Confidence Engine (differentiated confidence from multiple signals)
- Contradiction Detection (conflicting facts across pages)
- Evidence Coverage (percentage of claims supported by evidence)
- AI Reliability Score (HIGH/MEDIUM/LOW)
- Review Priority (HIGH/MEDIUM/LOW)
- Hallucination Firewall (claim validation)
- Processing Route tracking
"""
import re
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple
from models import AnalysisResult, ClassificationDecision, Evidence, ExtractedFact, PageResult


class EvidenceEngine:
    """Core evidence processing engine."""

    def __init__(self):
        self.contradiction_penalty = 0.15
        self.missing_field_penalty = 0.05
        self.ocr_penalty = 0.10

    def compute_confidence(self, fact: ExtractedFact, pages: List[PageResult] = None,
                          ocr_used: bool = False, language: str = "en") -> float:
        """Compute differentiated field-level confidence."""
        base = fact.confidence

        # Evidence quality: does the fact have supporting evidence?
        if fact.evidence and len(fact.evidence) > 0:
            evidence_confidence = max(e.confidence for e in fact.evidence)
            base = (base + evidence_confidence) / 2
        else:
            base *= 0.5  # No evidence = lower confidence

        # OCR penalty
        if ocr_used:
            base *= (1 - self.ocr_penalty)

        # Language penalty
        if language != "en":
            base *= 0.90

        # Field completeness bonus
        if fact.value and fact.value != "Not stated":
            if self._has_structured_format(fact.field, str(fact.value)):
                base = min(1.0, base + 0.05)

        return round(max(0.0, min(1.0, base)), 4)

    def _has_structured_format(self, field: str, value: str) -> bool:
        """Check if value has expected structured format."""
        if field == "patient_id":
            return bool(re.match(r'^[A-Z]{0,3}-?\d{2,}', value.strip()))
        if field == "batch":
            return bool(re.match(r'^BATCH-?\d+', value.strip(), re.IGNORECASE))
        return False

    def detect_contradictions(self, facts: List[ExtractedFact],
                             pages: List[PageResult] = None) -> List[Dict[str, Any]]:
        """Detect conflicting facts across pages."""
        contradictions = []

        # Group facts by field
        field_values: Dict[str, List[Dict]] = {}
        for fact in facts:
            if fact.value == "Not stated" or not fact.value:
                continue
            field = fact.field
            if field not in field_values:
                field_values[field] = []
            for ev in fact.evidence:
                field_values[field].append({
                    "value": fact.value,
                    "page": ev.page,
                    "text": ev.text[:200],
                })

        # Check for contradictions in key fields
        key_fields = ["patient_id", "product", "reaction", "severity", "batch"]
        for field in key_fields:
            if field in field_values and len(field_values[field]) > 1:
                values = field_values[field]
                unique_values = list(set(v["value"].strip().lower() for v in values))
                if len(unique_values) > 1:
                    contradictions.append({
                        "field": field,
                        "type": "CONFLICTING_VALUES",
                        "values": values,
                        "resolution": "Human review required",
                    })

        return contradictions

    def compute_evidence_coverage(self, facts: List[ExtractedFact]) -> Dict[str, Any]:
        """Calculate evidence coverage metrics."""
        total_claims = len([f for f in facts if f.value != "Not stated" and f.value])
        supported = len([f for f in facts if f.value != "Not stated" and f.value
                        and f.evidence and len(f.evidence) > 0])
        unsupported = total_claims - supported

        coverage = (supported / max(total_claims, 1)) * 100

        return {
            "total_claims": total_claims,
            "supported": supported,
            "unsupported": unsupported,
            "coverage_percent": round(coverage, 1),
        }

    def compute_reliability(self, coverage: float, contradiction_count: int,
                           ocr_used: bool, missing_fields: int,
                           avg_confidence: float) -> str:
        score = 1.0
        score *= (coverage / 100)
        score -= contradiction_count * 0.15
        score -= missing_fields * 0.05
        if ocr_used:
            score -= 0.10
        score *= avg_confidence
        score = max(0.0, min(1.0, score))
        if score >= 0.80:
            return "HIGH"
        elif score >= 0.55:
            return "MEDIUM"
        else:
            return "LOW"

    def compute_review_priority(self, reliability: str, contradiction_count: int,
                              missing_fields: int, ocr_used: bool,
                              language: str, confidence: float,
                              categories: List[str]) -> str:
        score = 0
        if reliability == "LOW":
            score += 3
        elif reliability == "MEDIUM":
            score += 1
        score += contradiction_count * 2
        score += min(missing_fields, 3)
        if ocr_used:
            score += 1
        if language != "en":
            score += 1
        if confidence < 0.6:
            score += 2
        elif confidence < 0.75:
            score += 1
        if len(categories) > 1:
            score += 1
        if score >= 4:
            return "HIGH"
        elif score >= 2:
            return "MEDIUM"
        else:
            return "LOW"

    def validate_claims(self, facts: List[ExtractedFact],
                       pages: List[PageResult] = None) -> List[Dict[str, Any]]:
        validated = []
        for fact in facts:
            if fact.value == "Not stated" or not fact.value:
                validated.append({"field": fact.field, "value": fact.value, "status": "NOT_STATED", "confidence": 0.0})
                continue
            supported = False
            if fact.evidence and len(fact.evidence) > 0:
                for ev in fact.evidence:
                    if ev.text and str(fact.value).lower() in ev.text.lower():
                        supported = True
                        break
            validated.append({
                "field": fact.field, "value": fact.value,
                "status": "SUPPORTED" if supported else "UNSUPPORTED",
                "confidence": fact.confidence,
                "evidence_count": len(fact.evidence) if fact.evidence else 0,
            })
        return validated

    def detect_prompt_injection(self, text: str) -> Dict[str, Any]:
        patterns = [
            r"ignore\s+(previous|all|above)\s+instructions",
            r"disregard\s+(previous|all|above)\s+instructions",
            r"forget\s+(previous|all|above)\s+instructions",
            r"you\s+are\s+now",
            r"new\s+instructions?:",
            r"system\s+prompt:",
            r"override\s+(previous|all)\s+instructions",
            r"do\s+not\s+follow",
            r"instead\s+of\s+the\s+above",
        ]
        detected = [p for p in patterns if re.search(p, text.lower())]
        return {
            "injection_detected": len(detected) > 0,
            "patterns_found": detected,
            "risk_level": "HIGH" if len(detected) > 1 else "MEDIUM" if detected else "LOW",
        }

    def compute_document_fingerprint(self, text: str) -> str:
        normalized = re.sub(r'\s+', ' ', text.lower().strip()[:5000])
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def compute_processing_route(self, ocr_used: bool, llm_used: bool,
                                vlm_used: bool, rag_used: bool,
                                rules_used: bool) -> str:
        parts = []
        if ocr_used:
            parts.append("OCR")
        if not ocr_used:
            parts.append("PDF")
        if rag_used:
            parts.append("RAG")
        if llm_used:
            parts.append("LLM")
        if vlm_used:
            parts.append("VLM")
        if rules_used:
            parts.append("Rules")
        return " → ".join(parts) if parts else "Direct"

    def build_evidence_graph(self, document_id: str, pages: List[PageResult],
                            facts: List[ExtractedFact], classification: str) -> Dict[str, Any]:
        nodes = [{"id": "document", "type": "DOCUMENT", "label": document_id}]
        edges = []
        for page in pages:
            nid = f"page_{page.page}"
            nodes.append({"id": nid, "type": "PAGE", "label": f"Page {page.page}", "confidence": page.confidence})
            edges.append({"from": "document", "to": nid, "type": "CONTAINS"})
        for i, fact in enumerate(facts):
            if fact.value == "Not stated" or not fact.value:
                continue
            fid = f"fact_{i}"
            nodes.append({"id": fid, "type": "FACT", "label": f"{fact.field}: {fact.value}", "confidence": fact.confidence})
            for ev in fact.evidence:
                if ev.page:
                    edges.append({"from": f"page_{ev.page}", "to": fid, "type": "SUPPORTS"})
        nodes.append({"id": "classification", "type": "CLASSIFICATION", "label": classification})
        for i, fact in enumerate(facts):
            if fact.value != "Not stated" and fact.value:
                edges.append({"from": f"fact_{i}", "to": "classification", "type": "SUPPORTS"})
        return {"nodes": nodes, "edges": edges}

    def compute_field_completeness(self, facts: List[ExtractedFact], category: str) -> Dict[str, Any]:
        if category == "SAFETY_REPORT_ICSR":
            required = ["patient_id", "product", "reaction"]
            optional = ["severity", "batch", "reporter", "narrative"]
        elif category == "QUALITY_COMPLAINT_PQC":
            required = ["product", "batch", "issue"]
            optional = ["photo_mentioned", "narrative"]
        elif category == "INFO_REQUEST_MI":
            required = ["actual_question"]
            optional = ["mi_topic", "product"]
        else:
            required = []
            optional = []
        present = []
        missing = []
        for field in required + optional:
            fact = next((f for f in facts if f.field == field), None)
            if fact and fact.value != "Not stated" and fact.value:
                present.append(field)
            else:
                missing.append(field)
        total = len(required) + len(optional)
        # Nothing required -> vacuously complete (avoids misleading 0%).
        completeness = (len(present) / total * 100) if total else 100.0
        return {
            "present": present, "missing": missing,
            "required_present": [f for f in present if f in required],
            "required_missing": [f for f in missing if f in required],
            "completeness_percent": round(completeness, 1),
        }


def compute_evidence_summary(result: AnalysisResult) -> Dict[str, Any]:
    engine = EvidenceEngine()
    validated_claims = engine.validate_claims(result.facts, result.pages)
    contradictions = engine.detect_contradictions(result.facts, result.pages)
    coverage = engine.compute_evidence_coverage(result.facts)
    primary_cat = result.categories[0].category if result.categories else "NOT_RELEVANT"
    completeness = engine.compute_field_completeness(result.facts, primary_cat)
    confidences = [f.confidence for f in result.facts if f.value != "Not stated" and f.value]
    avg_confidence = sum(confidences) / max(len(confidences), 1)
    missing_count = len(completeness["missing"])
    reliability = engine.compute_reliability(
        coverage["coverage_percent"], len(contradictions),
        result.ocr_confidence is not None, missing_count, avg_confidence,
    )
    categories = [c.category for c in result.categories]
    review_priority = engine.compute_review_priority(
        reliability, len(contradictions), missing_count,
        result.ocr_confidence is not None, result.language_flag,
        result.categories[0].confidence if result.categories else 0, categories,
    )
    route = engine.compute_processing_route(
        ocr_used=result.ocr_confidence is not None,
        llm_used=result.document_type == "LLM_ANALYZED",
        vlm_used=False, rag_used=bool(result.pages),
        rules_used=result.document_type != "LLM_ANALYZED",
    )
    # Prompt-injection defense: document content is analyzed for attempts to
    # manipulate the classifier. Detection is reported and routed to review;
    # it never silently changes the classification itself.
    prompt_injection = engine.detect_prompt_injection(result.extracted_text or "")
    evidence_graph = engine.build_evidence_graph(
        result.extracted_text[:50] if result.extracted_text else "document",
        result.pages, result.facts, primary_cat,
    )
    return {
        "validated_claims": validated_claims,
        "contradictions": contradictions,
        "evidence_coverage": coverage,
        "field_completeness": completeness,
        "ai_reliability": reliability,
        "review_priority": review_priority,
        "processing_route": route,
        "evidence_graph": evidence_graph,
        "avg_confidence": round(avg_confidence, 4),
        "prompt_injection": prompt_injection,
        "document_fingerprint": engine.compute_document_fingerprint(result.extracted_text),
    }

