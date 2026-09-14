# Known Limitations — CLINEVO Smart Inbox Assistant

Honest, evidence-based. VERIFIED = tested; CONFIGURED = built and env-gated but not live-verified.

1. **Oracle persistence:** CONFIGURED as the production target (portable schema, Oracle-ready
   DDL); live-verified on H2/local only. No Oracle instance was available to verify against.
2. **Scanned-PDF uploads to production backend:** 2/14 batch documents exceed Render's
   request-body limit (HTTP 413). Direct AI analysis of scanned/OCR documents is VERIFIED
   (15/15 batch). Not fixed to avoid touching working production ingress config.
3. **Multi-label over-trigger:** medical-info-request-001.pdf also emitted PQC and ICSR
   secondary labels at high confidence. Primary label correct; secondary confidence policy
   could be tightened.
4. **Extended safety fields (age/sex/weight/height/history/dose/route/dates/outcome):**
   core fields VERIFIED; extended fields best-effort per document structure.
5. **VLM image interpretation:** provider adapter CONFIGURED (env-gated); not VERIFIED —
   no vision credentials configured. System flags image evidence for human review instead
   of fabricating descriptions.
6. **Live IMAP mailbox:** not VERIFIED; synthetic/test email catalog used. An IMAP adapter
   must be env-credential driven and is documented as future work.
7. **Translation:** language detection VERIFIED (de/es); machine translation not performed —
   original-language evidence is preserved verbatim, per evidence-first policy.
8. **Handwriting:** OCR confidence surfaced; ambiguous handwriting routed to human review
   rather than guessed.

## Data safety
Synthetic healthcare data only; no real patient data. No credentials/keys in the repository.
LLM/VLM are optional (env-configured); the deterministic evidence engine is the default path.
