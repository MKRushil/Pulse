# Repository Guidelines

Contributor guide for this repo’s FastAPI backend and Vite/React UI. Backend has been simplified to a single, de‑identified Case pipeline and a single query route.

## Project Structure & Modules
- `Backend/`: FastAPI app (`main.py`), ingestion flow (`cases/`), retrieval/DB (`vector/`, `cbr/`), and LLM (`llm/`). Data lives in `Backend/data/` and logs in `Backend/logs/`.
- `ui/`: Vite + React + Tailwind. Entry `index.html`, sources under `src/`, dev proxy to `/api`.
- `Embedding/`: Standalone scripts for experiments (not required at runtime).

## Build, Run, and Test
- Backend (Python 3.10+):
  - Install: `pip install fastapi uvicorn weaviate-client`.
  - Run: `uvicorn Backend.main:app --reload`.
  - Probe: `curl -X POST :8000/api/case/save -H 'content-type: application/json' -d '{"basic":{},"inquiry":{}}'`.
- Frontend:
  - `cd ui && npm install`.
  - Dev: `npm run dev` (proxy to `:8000`). Build: `npm run build`.

## Ingestion & Query Flow
- De‑ID Ingestion (DCIP):
  1) Save raw JSON → `Backend/data/`.
  2) Normalize de‑ID view → keep `age/gender/chief/present/provisional`.
  3) Triage diagnosis (main/sub with weights) + embedding.
  4) Upload to Weaviate `Case` (anonymized `case_id`).
- Query: `POST /api/query` → `cbr/spiral.py` retrieves `Case` + `PulsePJ`, aggregates, builds prompt, returns `dialog` and `llm_struct`.

## Coding Style & Naming
- Python: PEP 8, 4‑space indent, snake_case. Keep routes thin in `main.py`; logic in `cases/`, `cbr/`, `vector/`, `llm/`.
- React: PascalCase components, camelCase variables. ESLint config in `ui/eslint.config.js`.

## Weaviate Schema (Case only)
- Class `Case` includes: `case_id`, `timestamp`, `age`, `gender`, `summary`, `chief_complaint`, `present_illness`, `provisional_dx`, `diagnosis_main`, `diagnosis_sub`, `embedding`, plus compatibility fields (`llm_struct`, etc.).

## Security
- Move secrets out of `Backend/config.py` to env vars in deployment. Keep keys out of commits.
