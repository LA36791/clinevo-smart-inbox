# Requirements Matrix — CLINEVO Smart Inbox (Development Copy)

Statuses reflect actual executed verification. Evidence = tool-verified HTTP responses / builds this session.

| # | Requirement | Implementation | Location | Verification | Result | Status |
|---|---|---|---|---|---|---|
| 1 | ICSR / PQC / MI / Not Relevant, multi-label, confidence, reason | Keyword-scored multi-bucket classifier | ai-service/main.py (analyze_text) | POST /analyze with PQC, MI, newsletter payloads | QUALITY_COMPLAINT_PQC, INFO_REQUEST_MI, NOT_RELEVANT each returned with confidence+reason | COMPLETE |
| 2 | Digital PDF extraction | pypdf per-page, page-tagged text | ai-service/main.py /analyze-document | synthetic_case.pdf via /api/analyze | 200, DIGITAL_TEXT_PDF, ICSR 0.90 | COMPLETE |
| 3 | Scanned PDF OCR + confidence | pdf2image + pytesseract, word-level avg conf | ai-service/main.py OCR fallback | scanned_case.pdf via /api/analyze | 200, SCANNED_OCR_PDF, OCR conf 0.93, page-1 evidence | COMPLETE |
| 4 | Portable OCR tool discovery | TESSERACT_CMD env + known install paths; shutil.which for poppler | ai-service/main.py (imports, analyze_document) | python -c pytesseract.get_tesseract_version() | Tesseract 5.4.0.20240606 found | COMPLETE |
| 5 | Fact extraction, Not stated, confidence, evidence | Label regex + Not-stated defaults | ai-service/main.py extract_value/extract_fact | scanned_case.pdf response | patient/product/reaction/severity/batch extracted; absent fields = "Not stated", conf 0.0 | COMPLETE |
| 6 | Angular review workflow (classify, facts, evidence, accept/override, timestamps) | Single-component app | frontend/src/app/app.html, app.ts | npm run build | BUILD OK (CSS budget warning only) | COMPLETE |
| 7 | /api/health, /api/analyze, /api/analyze-batch | Spring controllers | backend .../AnalysisController.java | curl each endpoint | 200 / 200 / 200 | COMPLETE |
| 8 | Batch with per-document envelope (filename/status/classification/confidence/time/review/keyFacts), max 15, per-file error isolation | Sequential loop reusing single flow | backend AiService.analyzeBatch | 2-file /api/analyze-batch live | 200; synthetic OK/ICSR/aid67, scanned OK/ICSR/aid68, keyFacts present | COMPLETE (2 docs; endpoint accepts up to 15) |
| 9 | 10-15 document dataset | Only 2 synthetic PDFs exist | data/ | directory inspection | digital 1, scanned 1; no PQC/MI/article/non-English fixtures; batch cap verified in code (15) but only 2 fixtures exercised live | PARTIAL |
| 10 | H2 persistence incl. generated IDs | JdbcTemplate + safe keyHolder.getKeys() | AnalysisPersistenceService.java | every analyze call returned analysisId (65-68 live) | SAVED each time | COMPLETE |
| 11 | Reviewer accept/override + audit timestamps + /api/audit?analysisId= | ReviewController + REVIEW_ACTION table + finder | backend review/audit endpoints | ACCEPT aid67 (id33), OVERRIDE aid68 (id34); /api/audit?analysisId=68 returns override row | COMPLETE |
| 12 | Multi-column repair / table rows / image-flag / language-flag | reorder_multicolumn_lines + extract_table_rows + detect_image_references + detect_language_flag (heuristic, evidence-preserving, no translation/invention) | ai-service/main.py | ai_smoke live: table 3 rows, image terms detected, non-en flagged; generic 'dose' text -> NOT_RELEVANT | COMPLETE (heuristic fallback; not full layout/translation engine) |
| 13 | Deployment | Render backend + AI | https://clinevo-smart-inbox.onrender.com, https://clinevo-smart-inbox-2.onrender.com | curl health both | 200 / 200 | COMPLETE |
| 14 | Frontend backend URL configurable + health/status/loading/error | window.__BACKEND_URL__ / localStorage override; same-origin default; localhost:8080 dev; /api/health check on load | frontend/src/app/app.ts, app.html | npm run build OK (CSS budget warning only) | COMPLETE |
| 15 | Documentation | README + docs | README.md, docs/ | this session | updated | COMPLETE |

Known limitations: heuristic (non-LLM) classification/extraction; single-page OCR fixtures; no automated test suite; thin dataset (2 PDFs, batch cap 15 in code but only 2 exercised live); table/image/language handling is detection+flagging, not full reconstruction/translation; MI question extraction needs 'Label: value' shape in PDFs, otherwise 'Not stated' by design.