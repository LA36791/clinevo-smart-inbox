# Final Release Baseline — CLINEVO Smart Inbox Assistant

Internal engineering record. Distinguishes VERIFIED / CONFIGURED / NOT YET VERIFIED.

## Current production commit
- Production lineage (`main`): `7845949` "Fix evidence coverage calculation" (deployed to Render)
- Preserved legacy lineage: `legacy-main` @ `c6ea202` (frozen fallback, NOT deployed)
- This release branch: `release-docs` (docs only, cut from `main`)

## Architecture (deployed)
Angular 20 frontend → Spring Boot (Java 21) backend → FastAPI AI service
- Frontend: https://clinevo-smart-inbox-3.onrender.com
- Backend:  https://clinevo-smart-inbox.onrender.com
- AI:       https://clinevo-smart-inbox-1.onrender.com (Swagger: /docs)

## Working endpoints (verified live)
- GET  /api/health (backend) → {"service":"Clinevo Smart Inbox Backend","status":"UP"} — VERIFIED
- GET  /health (AI) → {"status":"ok","version":"1.2.0"} — VERIFIED
- POST /api/analyze (multipart PDF) → HTTP 200, classification + facts + evidence — VERIFIED

## Verified behavior (live production test, icsr-form-001.pdf)
- document_type DIGITAL_TEXT_PDF
- classification SAFETY_REPORT_ICSR, confidence 0.91, one-line reason
- extracted: patient P-101, reporter Dr. Meera Iyer, product CardioRelax 50 mg, batch CR-4501, reaction, severity
- page-level evidence (page 1)
- missing fields returned as "Not stated"
- latency ~0.87 s round-trip (warm)

## Tests executed on release branch
- AI unit/E2E suites: 15/15 synthetic PDFs PASS (earlier verified run on this lineage)
- Backend build PASS; backend contract to AI verified live
- Angular production build PASS
- Legacy lineage local E2E: POST /api/analyze-document HTTP 200 (on legacy-main only)

## Known unverified assignment requirements
- Live Oracle persistence (H2/local verified; Oracle is documented production target, CONFIGURED not LIVE-VERIFIED)
- Live IMAP mailbox connection (synthetic/test mailbox only)
- VLM image interpretation (optional provider, CONFIGURED not VERIFIED)
- Handwriting OCR confidence values on scanned fixtures (PARTIALLY VERIFIED)

## Release policy
Docs-only changes on release-docs. No API, URL, CORS, or environment contract changes.
