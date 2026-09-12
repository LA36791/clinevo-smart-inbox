# Demo Guide (15 minutes)

## Start services

```
cd ai-service && .venv\Scripts\python.exe -m uvicorn main:app --port 8002
cd backend && ..\maven-temp\apache-maven-3.9.11\bin\mvn spring-boot:run
cd frontend && npm start
```

## Script

1. **Health** — open http://localhost:8080/api/health and http://localhost:8002/health.
2. **Digital ICSR** — upload `data/synthetic_case.pdf` in the Angular UI. Show SAFETY_REPORT_ICSR 0.90, facts (P-001, Product A, Nausea, Non-serious, BATCH-001), page-1 evidence, "Not stated" for absent fields.
3. **Scanned OCR ICSR** — upload `data/scanned_case.pdf`. Show SCANNED_OCR_PDF, OCR confidence 0.93, same fact/evidence behavior.
4. **Review** — accept analysis 33; override 34 to QUALITY_COMPLAINT_PQC with reviewer name + notes. Show "Audit action recorded".
5. **Audit** — GET /api/audit?analysisId=34 shows original AI value, reviewer value, actor, timestamp.
6. **Batch** — run the curl from docs/BATCH_RESULTS.md; show per-document timings and persistence.
7. **Category coverage** — POST /analyze on the AI service with PQC, MI, and newsletter text payloads; show QUALITY_COMPLAINT_PQC / INFO_REQUEST_MI / NOT_RELEVANT.

## Key talking points

- Evidence-first: every fact carries value + confidence + source (type/id/page/snippet).
- Missing data is "Not stated", never guessed; confidence 0.0.
- AI proposes, human decides; AI result and reviewer result are both persisted.
- OCR is local (Tesseract + Poppler) — no document content leaves the machine.
- Deployed: backend https://clinevo-smart-inbox.onrender.com, AI https://clinevo-smart-inbox-1.onrender.com (both health-checked 200).