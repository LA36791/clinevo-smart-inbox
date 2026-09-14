# Assignment Rubric Matrix — CLINEVO Smart Inbox Assistant

Statuses: VERIFIED (tested on this codebase) / PARTIAL / NOT VERIFIED (CONFIGURED only where noted).
Evidence = this repo's tests + live production checks (see FINAL_RELEASE_BASELINE.md).

| # | Requirement | Implementation | Evidence | Status | Risk | Minimal fix |
|---|---|---|---|---|---|---|
| A1 | Email/test mailbox intake | Synthetic email catalog + intake API | EmailCatalogController/Service, backend tests | PARTIAL | Low | Live IMAP adapter (optional, env-gated) |
| A2 | Sender/subject/date/body | Modeled in email catalog entities | Catalog service tests | VERIFIED | — | — |
| A3 | PDF attachments | Upload → /api/analyze | Live POST 200 on icsr-form-001.pdf | VERIFIED | — | — |
| A4 | Non-PDF attachments logged | Attachment metadata path | Code review, no dedicated test | PARTIAL | Low | Add unit test |
| A5 | Processed results queryable | Persistence + audit endpoints | Backend tests; /api/audit returns data | VERIFIED | — | — |
| B1 | Digital PDF direct extraction | PyMuPDF text layer | Live result DIGITAL_TEXT_PDF | VERIFIED | — | — |
| B2 | Labels/forms preserved | Field-label parser | Extracted facts match form fields | VERIFIED | — | — |
| B3 | Scanned PDF OCR | Tesseract pathway + OCR confidence | Scanned fixtures processed in 15/15 batch | VERIFIED | — | — |
| B4 | Handwriting confidence | OCR confidence + review flag | Handwritten fixtures routed to review | PARTIAL | Low | Document thresholds |
| B5 | Article/multi-column handling | Article router + case extraction | article-001..005 fixtures | VERIFIED | — | — |
| B6 | Patient-case extraction from articles | Case-section extractor | Literature fixtures tests | PARTIAL | Medium | Tighten boundaries vs references |
| B7 | Non-English detection | Language detection | report-de/es fixtures | VERIFIED | — | — |
| B8 | Translation/direct extraction | Direct extraction + preserved original | Non-English tests | PARTIAL | Medium | Optional translation provider |
| B9 | Original-language traceability | original_evidence retained | Evidence payloads include original text | VERIFIED | — | — |
| B10 | Table extraction structured | find_tables → columns/rows/page | 2 tables returned live | VERIFIED | — | — |
| B11 | Image description | Optional VLM adapter | CONFIGURED, not VERIFIED (no VLM key) | NOT VERIFIED | Low | Document as optional |
| B12 | Image review flag | Uncertainty → review_required | Review-routing tests | VERIFIED | — | — |
| B13 | 10–15 sentence summary | Grounded summary generator | Summary present in live output | PARTIAL | Low | Length enforcement for short docs |
| B14 | Relevance determination | NOT_RELEVANT bucket | Irrelevant fixture tests | VERIFIED | — | — |
| C1–C4 | Four categories, multi-label, confidence, reason | Multi-label classifier | Live 0.91 ICSR + reason; fixtures | VERIFIED | — | — |
| D1–D6 | Review UI (queue/class/conf/summary/accept/override) | Angular workbench | Frontend build PASS; accept/override E2E | VERIFIED | — | — |
| E1–E15 | Extended safety fields (age/sex/weight/height/history/dose/route/dates/outcome) | Core set extracted (patient/reporter/product/reaction/severity/narrative/batch); extended fields on best-effort | Live extraction of core set | PARTIAL | Medium | Add extended field patterns |
| F1–F4 | PQC (product/batch/problem/photo) | PQC extractor | quality-complaint-001 fixture | VERIFIED | — | — |
| G1–G2 | MI (question/product/topic) | MI extractor | medical-info-request-001 fixture | VERIFIED | — | — |
| H1–H4 | Traceability, field confidence, timestamps, AI decision records | Evidence objects with page+source; audit table | Live evidence w/ page 1; audit queryable | VERIFIED | — | — |
| I1–I3 | Synthetic data only, no real patient data, cloud-AI tradeoff documented | Synthetic corpus; README tradeoff section | Repo scan: no credentials | VERIFIED | — | — |
| J1–J2 | 10–15 doc batch + timing | Batch runner | 15/15 PASS with per-doc timing | VERIFIED | — | — |
| K1–K4 | Literature screening bonus | Article case separation | article fixtures | PARTIAL | Low | Multi-case separation polish |
| L1–L8 | Documentation | README + docs/ | This release adds matrix/baseline/results | VERIFIED | — | — |

## Oracle status
CONFIGURED as production target (portable schema); LIVE-VERIFIED only on H2/local. Not claimed as live.

## Data safety
Synthetic data only. No API keys committed. LLM/VLM providers optional via env, deterministic fallback default.
