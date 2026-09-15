# CLINEVO Smart Inbox Assistant — Technical Report

**Evidence-First Review OS for Healthcare Document Triage**

> The difficult part was not getting AI to read a PDF. It was making the AI's answer easy for another human to verify.

## 1. Executive Summary

The Smart Inbox Assistant triages inbound healthcare documents (PDFs) into four categories — Safety Report / ICSR, Quality Complaint / PQC, Information Request / MI, and Not Relevant — extracts structured facts with page-level evidence and confidence, and routes the result to a human reviewer whose ACCEPT/OVERRIDE decision is persisted in a timestamped audit trail. It runs fully offline with a deterministic pipeline; an optional OpenAI-compatible LLM can be enabled via environment variables without changing the evidence contract.

Live system: [Frontend](https://clinevo-smart-inbox-3.onrender.com) · [Backend health](https://clinevo-smart-inbox.onrender.com/api/health) · [AI health](https://clinevo-smart-inbox-1.onrender.com/health) · [Swagger](https://clinevo-smart-inbox-1.onrender.com/docs) · [Source](https://github.com/LA36791/clinevo-smart-inbox)

## 2. Problem

A pharmacovigilance inbox receives mixed documents: adverse-event reports, product-quality complaints, medical-information requests, and irrelevant material. Manual triage is repetitive and hard to audit. The core difficulty is trust: an AI answer a reviewer cannot verify is worse than no answer.

## 3. Architecture

Angular reviewer UI (:4200) → Spring Boot API (Java 21, :8080) → FastAPI AI service (:8002, pypdf / Poppler + Tesseract OCR / BM25 RAG) → structured JSON (categories, facts, evidence, confidence, evidence_summary) → Spring Boot persistence (H2 dev; Oracle-target schema) → Angular review → audit trail.

Clean service boundaries: the backend never classifies; the AI service never persists; the reviewer UI never talks to the AI service directly.

## 4. Evidence-First Design

Every extracted fact carries value, confidence, page number, and a verbatim source snippet. The AI service computes an evidence summary per document: total/supported/unsupported claims, evidence coverage percent, contradiction detection, per-category field completeness, a reliability grade (HIGH/MEDIUM/LOW), a review-priority heuristic (LOW/MEDIUM/HIGH/CRITICAL — a prototype reviewer-attention heuristic, not a validated medical risk score), a processing route (DIGITAL / OCR / RAG / LLM), and prompt-injection detection. Missing information is never guessed: value "Not stated", confidence 0.0, no evidence.

Evidence coverage is computed from actual claims — a document with 6 stated fields all backed by page snippets reports 100% (6/6); one with unsupported fields reports the real percentage and the reason.

## 5. PDF Processing

- **Digital**: pypdf per-page extraction with page-tagged text, label/value and table-row heuristics, multi-column line reordering (best-effort).
- **Scanned**: Poppler rasterization + Tesseract OCR with per-word confidence averaged per page; OCR confidence < 0.85 forces human review. Portable tool discovery (`TESSERACT_CMD`, PATH), tested on Windows with Tesseract 5.4.
- **Non-English**: non-ASCII-ratio detection; original text retained as evidence; `translation_status: NOT_CONFIGURED` when no provider is set — the system never fabricates a translation.
- **Images**: detection and metadata only; semantic interpretation is explicitly not claimed (`image_review_required: true`). VLM routing is stubbed behind configuration.

## 6. Classification and Extraction

Deterministic weighted-keyword scoring across the four buckets with multi-label support, per-category confidence, one-line reason, and trigger evidence. ICSR extraction covers patient (age, sex, weight, height, history), reporter, product (dose, route, dates, batch), reaction (onset, outcome, severity), and narrative; PQC covers product/batch/defect/photo-mentioned; MI extracts the actual question via a genuine-question gate so generic statements are not misread as requests.

## 7. Human Review and Audit

The Angular reviewer shows classification, confidence, reason, evidence coverage, review priority, missing fields, per-fact evidence with page numbers, processing route and time, and — after a decision — a loadable audit table (action, reviewer, original vs final category, timestamp, notes) fetched from `GET /api/audit?analysisId=`. Review actions are validated server-side (ACCEPT/OVERRIDE only; anything else returns HTTP 400).

## 8. Batch

`POST /api/analyze-batch` (cap 15) processes sequentially with per-document status, classification, confidence, processing time, and keyFacts. One failing document becomes a per-file ERROR result; files beyond the cap are returned as SKIPPED with a reason — nothing is silently discarded.

## 9. Testing

42 unit tests over the evidence engine (coverage, contradictions, reliability, priority, routes, completeness, confidence calibration, injection detection, fingerprints, evidence graph), adversarial and import tests, live end-to-end batch runs over the 15-fixture synthetic corpus, and live review/audit/invalid-action checks. All content in `data/` is synthetic; no PHI.

## 10. Security, Tradeoffs, Production Path

No secrets in the repository; configuration via environment variables. Uploads are size-limited multipart PDFs handled through safe temporary files. Deterministic mode: private, free, fast, fully reproducible — weaker on ambiguous language. Cloud LLM mode (opt-in): richer extraction/reasoning, but data leaves the machine, with cost, latency, and governance tradeoffs; the deterministic provider remains the fallback and the evidence contract is unchanged.

Development persistence is H2 file mode. The schema (8 tables: EMAIL_MESSAGE, DOCUMENT, ANALYSIS_RESULT, CLASSIFICATION, EXTRACTED_FACT, EVIDENCE, REVIEW_ACTION, PROCESSING_LOG) is portable SQL; the production target is Oracle via a Spring profile with the same schema and generated IDs — this is documented and scaffolded, not live-tested against an Oracle instance.

## 11. Limitations (truthful)

Heuristic (non-LLM by default) classification/extraction; OCR page attribution verified on single-page scanned fixtures; table extraction best-effort; image handling is detection-only; no live mailbox connectivity (synthetic ingestion + documented IMAP/Graph adapter path); Oracle profile not exercised against a real instance; batch is sequential.

## 12. Demo Flow (10–15 min)

1. Digital ICSR (`synthetic_case.pdf`): classification 91%, facts, page evidence, coverage.
2. Scanned case (`scanned_case.pdf`): OCR confidence, review flag.
3. PQC (`pqc_001.pdf`) and MI (`mi_001.pdf`): different classification paths.
4. Adversarial document (`adversarial_001.pdf`): uncertainty surfaced, human review required.
5. Accept, then Override with a reason.
6. Audit trail table: timestamped decision history.
7. Batch via `curl -F "files=@data/synthetic_case.pdf" ... http://localhost:8080/api/analyze-batch`.

## 13. Reflection

Ganesh Chaturthi is traditionally associated with auspicious beginnings, wisdom, and the removal of obstacles. The engineering analogy: this system removes practical workflow obstacles — repetitive triage, manual extraction, hard-to-trace decisions — while keeping human responsibility firmly in the loop. It is an engineering analogy only, not a comparison of scripture with software.
