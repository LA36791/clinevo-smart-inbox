# CLINEVO Smart Inbox Assistant (Development Copy)

Pharmacovigilance document triage: upload a PDF, get AI classification + fact extraction with page-level evidence, and make the final reviewer decision.

**AI proposes. Evidence supports. Human decides. Audit preserves accountability.**

## Architecture

```
Angular (reviewer UI, :4200)
  ↓ POST /api/analyze | /api/analyze-batch | /api/review
Spring Boot (Java 21, :8080)
  ↓ POST /analyze-document
FastAPI AI service (:8002)  → pypdf (digital) | Poppler + Tesseract OCR (scanned)
  ↓ result JSON (categories, facts, evidence, confidence, summary)
Spring Boot → H2 persistence (DOCUMENT, ANALYSIS_RESULT, CLASSIFICATION,
EXTRACTED_FACT, EVIDENCE, PROCESSING_LOG, REVIEW_ACTION)
```

## Stack
Angular · Spring Boot · FastAPI · pypdf · pdf2image/Poppler · Tesseract · H2

## Prerequisites
- JDK 21, Node 18+, Python 3.12
- Tesseract OCR: `C:\Program Files\Tesseract-OCR\tesseract.exe` (auto-discovered; override with `TESSERACT_CMD` env var)
- Poppler on PATH (winget `oschwartz10612.Poppler` works)

## Setup & Run

```powershell
# 1. AI service
cd ai-service
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn main:app --port 8002

# 2. Backend
cd backend
..\maven-temp\apache-maven-3.9.11\bin\mvn spring-boot:run

# 3. Frontend
cd frontend
npm install
npm start
```

## Environment variables

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `AI_SERVICE_URL` | backend | `http://127.0.0.1:8002` | AI service base URL (Render sets this in prod) |
| `PORT` | backend | `8080` | server port |
| `TESSERACT_CMD` | AI service | auto-discovered | tesseract.exe path override |

No secrets are stored in the repository.

## API endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | backend health |
| `/api/analyze` | POST (multipart `file`) | analyze one PDF |
| `/api/analyze-batch` | POST (multipart `files`) | analyze many PDFs, per-document timing |
| `/api/review` | POST | reviewer ACCEPT / OVERRIDE |
| `/api/audit?analysisId=` | GET | reviewer audit trail |
| `/health` | GET (AI) | AI service health |
| `/analyze` | POST (AI, JSON) | analyze email text |
| `/analyze-document` | POST (AI, multipart) | analyze PDF |

## Tests / batch

```
# single + scanned
curl -F "file=@data/synthetic_case.pdf" http://localhost:8080/api/analyze
curl -F "file=@data/scanned_case.pdf" http://localhost:8080/api/analyze
# batch
curl -F "files=@data/synthetic_case.pdf" -F "files=@data/scanned_case.pdf" http://localhost:8080/api/analyze-batch
```

Verified results: see `docs/BATCH_RESULTS.md` and `docs/REQUIREMENTS_MATRIX.md`.

## Design decisions

- **Classification**: deterministic keyword-scored multi-bucket engine (ICSR / PQC / MI / NOT_RELEVANT) — reproducible, offline, no data egress; each category returns confidence + one-line reason + evidence.
- **OCR**: local Tesseract; word-level confidence averaged per page; low confidence (< 0.85) forces human review. No document content leaves the machine.
- **Non-English detection**: non-ASCII ratio heuristic flags the document, retains original text as evidence, routes to human review — no fabricated translation.
- **Not stated policy**: missing information is never guessed; value "Not stated", confidence 0.0, no evidence.
- **Evidence-first**: every fact carries value + confidence + source (type, id, page, snippet). Reviewer sees WHAT/WHY/WHERE/HOW CONFIDENT.
- **AI vs reviewer distinction**: AI result persisted at analysis time; reviewer ACCEPT/OVERRIDE stored separately in REVIEW_ACTION with original AI value, final value, actor, notes, timestamp.
- **Cloud AI data trade-off**: an LLM would improve ambiguous extraction but would send patient data to a third party. The current design keeps everything local; swapping in an LLM would require a data-processing agreement and should keep the deterministic evidence layer.

## Limitations
- Heuristic engine: no multi-column/table/image-description/translation handling beyond flagging.
- Small synthetic dataset (2 PDFs); batch verified with 2 documents.
- H2 file database is local-only; Oracle/managed DB is the production target (schema is portable SQL).
- Frontend not hosted as a static site (build succeeds; API base URL configurable in `frontend/src/app/app.ts`).

## Deployment
- Backend: https://clinevo-smart-inbox.onrender.com (`/api/health` verified 200)
- AI: https://clinevo-smart-inbox-2.onrender.com (`/health` verified 200)

## Sample output (actual run)

```json
{"document_type":"SCANNED_OCR_PDF",
 "categories":[{"category":"SAFETY_REPORT_ICSR","confidence":0.9,
   "reason":"Safety/adverse-event indicators were detected.",
   "evidence":[{"source_type":"PDF_OCR","page":1,"confidence":0.93,...}]}],
 "facts":[{"field":"patient_id","value":"P-002","confidence":0.93,...},
          {"field":"actual_question","value":"Not stated","confidence":0.0,"evidence":[]}],
 "human_review_required":true,"processing_time_ms":7885}
```

Demo walkthrough: `docs/DEMO_GUIDE.md`.