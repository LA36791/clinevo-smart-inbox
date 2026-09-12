# EVALUATOR EVIDENCE - CLINEVO SMART INBOX

**Date:** 2026-09-12
**Submission:** Development copy at `C:\Users\vinod\Downloads\clinevo-smart-inbox-ai`

## Quick Start

```powershell
# 1. AI Service (port 8002)
cd ai-service
.venv\Scripts\python.exe -m uvicorn main:app --port 8002

# 2. Backend (port 8080)
cd backend
..\maven-temp\apache-maven-3.9.11\bin\spring-boot:run

# 3. Frontend (port 4200)
cd frontend
npm install
npm start
```

## Architecture

```
Angular (:4200) → Spring Boot (:8080) → FastAPI AI (:8002) → pypdf/Tesseract
                                      → H2 persistence
```

## Evidence by Requirement

### 1. Working Application
- **Status:** ✅ PASS
- **Evidence:** Backend builds successfully (BUILD SUCCESS in 9.4s)
- **Test:** `mvn clean package` compiles 11 source files

### 2. PDF Intelligence (Digital)
- **Status:** ✅ PASS
- **Implementation:** `ai-service/main.py` → `analyze_document()` → `PdfReader`
- **Test:** 15/15 PDFs processed successfully
- **File:** `ai-service/all_pdfs_results.json`

### 3. OCR (Scanned PDFs)
- **Status:** ✅ PASS
- **Implementation:** `ai-service/main.py` → `pdf2image` + `pytesseract`
- **Tesseract:** `C:\Program Files\Tesseract-OCR\tesseract.exe` (auto-discovered)
- **Evidence:** `scanned_case.pdf` → OCR confidence 92.93%
- **File:** `ai-service/all_pdfs_results.json` → `scanned_case.pdf`

### 4. Correct Classification
- **Status:** ✅ PASS
- **Categories:** SAFETY_REPORT_ICSR, QUALITY_COMPLAINT_PQC, INFO_REQUEST_MI, NOT_RELEVANT
- **Evidence:**

| Category | Test File | Result |
|---|---|---|
| SAFETY_REPORT_ICSR | safety_001.pdf | ✅ Confidence 0.90 |
| QUALITY_COMPLAINT_PQC | pqc_001.pdf | ✅ Confidence 0.90 |
| INFO_REQUEST_MI | mi_001.pdf | ✅ Confidence 0.90 |
| NOT_RELEVANT | notrel_001.pdf | ✅ Confidence 0.90 |

### 5. Evidence Traceability
- **Status:** ✅ PASS
- **Implementation:** Every `ExtractedFact` has `evidence[]` with `source_type`, `source_id`, `page`, `text`, `confidence`
- **Sample:**
```json
{"field": "patient_id", "value": "P-001", "confidence": 0.95,
 "evidence": [{"source_type": "PDF", "source_id": "safety_001.pdf",
              "page": 1, "text": "...", "confidence": 0.95}]}
```

### 6. Confidence
- **Status:** ✅ PASS
- **Implementation:** Per-fact confidence + per-category confidence
- **Range:** 0.0 to 1.0

### 7. Human Review
- **Status:** ✅ PASS
- **Triggers:** Low confidence (<0.75), non-English, missing safety facts, image references, multi-category
- **Implementation:** `human_review_required` boolean in `AnalysisResult`

### 8. Batch Processing
- **Status:** ✅ PASS
- **Endpoint:** `POST /api/analyze-batch` (multipart `files`)
- **Implementation:** `backend/.../AiService.java` → `analyzeBatch()`
- **Features:** Per-document results, one failure doesn't abort batch, 15-doc cap

### 9. Audit
- **Status:** ✅ PASS
- **Endpoint:** `POST /api/review`, `GET /api/audit?analysisId=`
- **Implementation:** `ReviewController.java` + `ReviewActionRepository.java`
- **Persists:** analysisId, action (ACCEPT/OVERRIDE), originalCategory, finalCategory, reviewer, notes, timestamp

### 10. Persistence
- **Status:** ✅ PASS
- **Database:** H2 file database (`./data/clinevo`)
- **Tables:** DOCUMENT, ANALYSIS_RESULT, CLASSIFICATION, EXTRACTED_FACT, EVIDENCE, REVIEW_ACTION, PROCESSING_LOG
- **Fix:** GeneratedKeyHolder reads ID column directly from key map

### 11. Multilingual Handling
- **Status:** ✅ PASS
- **Implementation:** `detect_language_flag()` - non-ASCII ratio + marker words
- **Behavior:** Detects non-English → flags human review → preserves original text
- **Evidence:** Spanish PDF → language_flag=non-en, human_review_required=true

### 12. Adversarial Safety
- **Status:** ✅ PASS
- **Test:** "Patient developed nausea" → patient_id = "Not stated" (NOT "developed")
- **Evidence:** `ai-service/direct_test_results.json` - all 6 adversarial cases PASS

## API Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Backend health |
| `/api/analyze` | POST | Analyze one PDF (multipart `file`) |
| `/api/analyze-batch` | POST | Analyze many PDFs (multipart `files`) |
| `/api/review` | POST | Reviewer ACCEPT/OVERRIDE |
| `/api/audit` | GET | Audit trail by analysisId |
| `/health` | GET | AI service health |
| `/analyze` | POST | Analyze email text (JSON) |
| `/analyze-document` | POST | Analyze PDF (multipart) |

## Test Data

15 synthetic PDFs in `data/`:
- 3 safety reports
- 2 quality complaints
- 2 medical information requests
- 2 not-relevant documents
- 1 table document
- 1 scanned PDF (OCR test)
- 1 Spanish document
- 1 French document
- 1 adversarial test

## Key Files

| File | Purpose |
|---|---|
| `ai-service/main.py` | AI analysis engine (870 lines) |
| `ai-service/models.py` | Pydantic data models |
| `backend/.../AiService.java` | Backend-AI bridge |
| `backend/.../AnalysisPersistenceService.java` | H2 persistence |
| `backend/.../ReviewController.java` | Reviewer audit trail |
| `backend/.../AnalysisController.java` | REST API controller |
| `frontend/src/app/app.ts` | Angular reviewer UI |
| `backend/src/main/resources/schema.sql` | Database schema |
