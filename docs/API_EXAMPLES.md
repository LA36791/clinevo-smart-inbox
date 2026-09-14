# API Examples — CLINEVO Smart Inbox Assistant

Base URLs (production):
- Backend:  https://clinevo-smart-inbox.onrender.com
- AI:       https://clinevo-smart-inbox-1.onrender.com (Swagger: /docs)
- Frontend: https://clinevo-smart-inbox-3.onrender.com

## 1. Backend health
```bash
curl https://clinevo-smart-inbox.onrender.com/api/health
```
```json
{"service":"Clinevo Smart Inbox Backend","status":"UP"}
```

## 2. AI health
```bash
curl https://clinevo-smart-inbox-1.onrender.com/health
```
```json
{"status":"ok","service":"clinevo-smart-inbox-ai","version":"1.2.0"}
```

## 3. Analyze a PDF (VERIFIED live)
```bash
curl -X POST https://clinevo-smart-inbox.onrender.com/api/analyze \
  -F "file=@sample-data/pdfs/digital/icsr-form-001.pdf"
```
Measured response (abridged, real output):
```json
{
  "document_type": "DIGITAL_TEXT_PDF",
  "categories": [
    {"category": "SAFETY_REPORT_ICSR", "confidence": 0.91,
     "reason": "Safety/adverse-event indicators were detected."}
  ],
  "facts": [
    {"field": "patient",  "value": "P-101", ...},
    {"field": "reporter", "value": "Dr. Meera Iyer", ...},
    {"field": "product",  "value": "CardioRelax 50 mg Tablets", ...},
    {"field": "batch",    "value": "CR-4501", ...},
    {"field": "reaction", "value": "Nausea and vomiting", ...},
    {"field": "severity", "value": "Non-serious", ...},
    {"field": "lot",      "value": "Not stated", ...}
  ],
  "evidence": [
    {"page": 1, "text": "[Page 1] SYNTHETIC ICSR REPORT FORM\nPatient: P-101 ..."}
  ],
  "tables": [...],
  "processing_time_ms": 870
}
```
Missing information is returned as `"Not stated"` with confidence 0 — never inferred.

## 4. AI direct analysis (independent testability)
```bash
curl -X POST https://clinevo-smart-inbox-1.onrender.com/analyze-document \
  -F "file=@sample.pdf"
```
Same evidence-first schema; lets the AI layer be tested without the backend.

## 5. Review / audit
```bash
curl https://clinevo-smart-inbox.onrender.com/api/audit
```
Returns persisted reviewer actions (accept/override) with timestamps and
previous/new decisions. AI results are never silently overwritten.
