# Implementation Baseline

Recorded before/while modifying the development copy.

## Environment
- Java: JDK 21 (Eclipse Adoptium)
- Build: local Maven distribution `maven-temp/apache-maven-3.9.11`
- Python: 3.12, venv at `ai-service/.venv`
- Tesseract: 5.4.0.20240606 at `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Poppler: 25.07.0 via winget (on PATH)
- Node/Angular: frontend builds with npm (`npm run build` OK)

## Baseline state found
- Backend + AI + H2 persistence working; single `/api/analyze` verified (analysisId + SAVED).
- Scanned OCR **broken locally**: hardcoded `poppler_path="/usr/bin"` and `pytesseract.tesseract_cmd="/usr/bin/tesseract"` (Linux paths).
- Batch endpoint absent (later added).
- `keyHolder.getKey()` used directly in AnalysisPersistenceService — H2 multi-key risk (later made safe).
- `application.properties` had hardcoded Render URL (restored to `${AI_SERVICE_URL:...}`).
- No README/docs; `docs/` empty.

## Fixes applied (smallest viable change each)
1. Portable Tesseract discovery + removed Linux-hardcoded override (`ai-service/main.py`).
2. Portable Poppler discovery via `shutil.which("pdfinfo")`.
3. Safe generated-key handling (`AnalysisPersistenceService.java:135`).
4. `analyzeBatch()` + `POST /api/analyze-batch`.
5. Config env-overridable AI URL.
6. Fact fields reporter/narrative/issue/photo_mentioned/mi_topic + non-English flagging.

## Post-fix verification (actual runs)
- `pytesseract.get_tesseract_version()` → 5.4.0.20240606
- scanned_case.pdf → 200, SCANNED_OCR_PDF, OCR conf 0.93
- batch (2 files) → 200, analysisIds 33/34, timings 85ms/4757ms
- ACCEPT/OVERRIDE → 200, audit rows persisted with timestamps
- PQC / MI / NOT_RELEVANT classifications → correct categories returned
- Render backend + AI health → 200/200
- Angular production build → OK
- Secret scan (regex for AWS/API keys) → clean