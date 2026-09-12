# Batch Results (actual executed run — 2026-09-12 session)

Command:

```
curl -F "files=@data/synthetic_case.pdf" -F "files=@data/scanned_case.pdf" `
  http://localhost:8080/api/analyze-batch
```

Result: HTTP 200, JSON array of 2 results.

| Document | status | Classification | Confidence | Batch time | analysisId | humanReview | keyFacts |
|---|---|---|---|---|---|---|---|
| synthetic_case.pdf | OK | SAFETY_REPORT_ICSR | 0.90 | 2 ms | 67 | true | patient_id P-001, product Product A, reaction Nausea, severity Non-serious |
| scanned_case.pdf | OK | SAFETY_REPORT_ICSR | 0.90 (OCR 0.929) | 3247 ms | 68 | true | reaction Headache, severity Serious, batch BATCH-002 |

- Success: 2/2, failures: 0 (one bad file cannot abort the batch; ERROR envelope returned per file).
- Per-document processingTimeMs + backend analysisId present for every document.
- Reviewer actions after batch: ACCEPT on 67 (audit id 33), OVERRIDE (ICSR -> QUALITY_COMPLAINT_PQC) on 68 (audit id 34); both persisted with reviewer + notes + actionTimestamp; /api/audit?analysisId=68 returns the override row.

Scaling: the endpoint caps at 15 files (assignment max); the full 10-15 fixture set is PARTIAL — only the 2 existing synthetic PDFs were exercised live (see REQUIREMENTS_MATRIX #9).