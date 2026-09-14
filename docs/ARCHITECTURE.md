# Architecture — CLINEVO Smart Inbox Assistant

```
                ┌──────────────────────────────┐
                │   Angular 20 Frontend        │
                │  clinevo-smart-inbox-3       │
                │  inbox • review • audit UI   │
                └──────────────┬───────────────┘
                               │ REST (multipart PDF, JSON)
                ┌──────────────▼───────────────┐
                │   Spring Boot (Java 21)      │
                │  clinevo-smart-inbox         │
                │  /api/analyze  /api/health   │
                │  review • audit • persistence│
                └──────────────┬───────────────┘
                               │ AI_SERVICE_URL (env)
                ┌──────────────▼───────────────┐
                │   FastAPI AI Service         │
                │  clinevo-smart-inbox-1       │
                │  /analyze  /analyze-document │
                │  /health  /docs (Swagger)    │
                └──────────────┬───────────────┘
                               │
        ┌──────────────────────┼───────────────────────┐
        ▼                      ▼                       ▼
  PDF text layer         Tesseract OCR          Optional LLM/VLM
  (digital PDFs)         (scanned, confidence)  (env-gated providers)
        └──────────────────────┼───────────────────────┘
                               ▼
                    Evidence Engine (deterministic default)
                    classification • fact extraction • evidence •
                    confidence • review routing
                               │
                               ▼
                  H2 (local) / Oracle (production target)
```

## Request flow (verified live)
1. Angular uploads PDF → `POST /api/analyze` (multipart).
2. Spring Boot forwards to FastAPI `AI_SERVICE_URL` (env-driven; no hardcoded URL).
3. AI service routes the document: digital text vs OCR vs article vs non-English.
4. Deterministic evidence engine extracts facts, each with value, confidence,
   source document, page, evidence text; missing facts are `"Not stated"`.
5. Multi-label classification returns categories + confidence + one-line reason.
6. Backend persists analysis; Angular review UI shows facts/evidence; reviewer
   Accept/Override writes a timestamped audit record.

## Modularity
- AI providers (LLM/VLM/OCR) are replaceable adapters behind env configuration.
- Deterministic fallback guarantees the demo works without external AI credentials.
- Persistence uses a portable schema; Oracle is the documented production target.
