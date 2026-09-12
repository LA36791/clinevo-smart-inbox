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
- **LLM integration**: optional OpenAI-compatible LLM for document understanding, classification, and fact extraction. Configured via `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`, `LLM_ENABLED` env vars. Falls back to deterministic provider when unavailable.
- **Hybrid RAG**: page-aware chunking with BM25 retrieval. Chunks preserve document/page metadata and evidence location. No external vector database required.
- **VLM routing**: scanned/image-heavy documents can be routed for visual understanding when VLM is available. Falls back to OCR/deterministic when unavailable.
- **Cloud AI data trade-off**: LLM improves ambiguous extraction but sends data to a third party. Configured via environment variables; deterministic fallback always available.

## Optional AI Configuration

| Variable | Default | Purpose |
|---|---|---|
| `LLM_API_KEY` | (none) | API key for OpenAI-compatible LLM |
| `LLM_API_BASE` | `https://api.openai.com/v1` | LLM API base URL |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `LLM_ENABLED` | `false` | Enable LLM (requires API key) |

When LLM is unavailable or disabled, the deterministic provider is used automatically.

## Limitations
- LLM requires API key and network access; deterministic fallback always available.
- Table extraction is best-effort (pipe/space delimited).
- Image detection only; visual interpretation requires VLM configuration.
- Multi-column layout uses lightweight line reordering.
- H2 file database is local-only; Oracle/managed DB is the production target (schema is portable SQL).

## Deployment
- Frontend: https://clinevo-smart-inbox-3.onrender.com
- Backend: https://clinevo-smart-inbox.onrender.com (`/api/health` verified 200)
- AI: https://clinevo-smart-inbox-1.onrender.com (`/health` verified 200)
- AI Swagger: https://clinevo-smart-inbox-1.onrender.com/docs

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