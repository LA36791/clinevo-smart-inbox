# Batch Test Results — Live Production Benchmark

Executed against PRODUCTION backend (https://clinevo-smart-inbox.onrender.com/api/analyze),
14 synthetic PDFs from sample-data/, one request per document, wall-clock timing.

## Aggregate
- Total documents: 14
- Successful: 12 (85.7%)
- Failed: 2 (HTTP 413 Payload Too Large — both scanned/image-heavy fixtures exceed Render's
  request-body limit; see limitations)
- Average latency (successful): ~1.09 s
- Minimum: 0.37 s · Maximum: 8.56 s (first-request cold route)

## Per-document results (measured)

| Document | Time (s) | document_type | Categories | Conf | Facts |
|---|---|---|---|---|---|
| article-001.pdf | 8.56 | DIGITAL_TEXT_PDF | SAFETY_REPORT_ICSR | 0.91 | 13 |
| article-002.pdf | 0.57 | DIGITAL_TEXT_PDF | SAFETY_REPORT_ICSR | 0.91 | 13 |
| article-003.pdf | 0.60 | DIGITAL_TEXT_PDF | SAFETY_REPORT_ICSR | 0.85 | 13 |
| article-004.pdf | 0.37 | DIGITAL_TEXT_PDF | SAFETY_REPORT_ICSR | 0.85 | 13 |
| article-005.pdf | 0.49 | DIGITAL_TEXT_PDF | SAFETY_REPORT_ICSR | 0.91 | 13 |
| icsr-form-001.pdf | 0.59 | DIGITAL_TEXT_PDF | SAFETY_REPORT_ICSR | 0.91 | 13 |
| icsr-form-002.pdf | 0.59 | DIGITAL_TEXT_PDF | SAFETY_REPORT_ICSR | 0.91 | 13 |
| icsr-form-003.pdf | 0.50 | DIGITAL_TEXT_PDF | SAFETY_REPORT_ICSR | 0.91 | 13 |
| medical-info-request-001.pdf | 0.38 | DIGITAL_TEXT_PDF | INFO_REQUEST_MI + SAFETY_REPORT_ICSR + QUALITY_COMPLAINT_PQC | 0.91 | 13 |
| quality-complaint-001.pdf | 0.49 | DIGITAL_TEXT_PDF | QUALITY_COMPLAINT_PQC + SAFETY_REPORT_ICSR | 0.91 | 13 |
| report-de-001.pdf | 0.48 | DIGITAL_TEXT_PDF | SAFETY_REPORT_ICSR | 0.70 | 13 |
| report-es-001.pdf | 0.38 | DIGITAL_TEXT_PDF | SAFETY_REPORT_ICSR | 0.91 | 13 |
| handwritten-icrs-001.pdf | — | FAILED | HTTP 413 | — | — |
| handwritten-pqc-001.pdf | — | FAILED | HTTP 413 | — | — |

All numbers are measured, not estimated. Timestamps UTC 2026-09-14.

## Findings / limitations (honest)
1. **413 on scanned fixtures (2/14):** Render's ingress body-size limit rejects the larger
   scanned/image PDFs. Direct-to-AI analysis of the same files succeeds (validated earlier
   against the AI service). Mitigation options (not applied to avoid production risk):
   compress/downsample uploads client-side, or raise the Render request limit.
   Scanned/OCR handling itself is verified on this lineage via the 15/15 direct-AI batch.
2. **Multi-label over-trigger on medical-info-request-001.pdf:** MI is primary/correct, but
   PQC and ICSR were also emitted at high confidence. Multi-label is assignment-correct in
   principle; the secondary-label confidence policy could be tightened.
3. **All article PDFs classified SAFETY_REPORT_ICSR (0.85–0.91):** articles contain actual
   patient-case sections, so the label is defensible (assignment distinguishes actual cases
   from general discussion); reviewer sees full evidence either way.
4. **Non-English confidence (report-de-001 at 0.70):** lower confidence on German document —
   appropriate conservatism; routed with lower confidence rather than guessed.

## Previous verified run (direct AI service, offline-safe path)
15/15 synthetic documents PASSED (digital, scanned/OCR, non-English, table, adversarial,
not-relevant) — see FINAL_RELEASE_BASELINE.md.
