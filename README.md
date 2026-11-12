# InsureMate AI: hospital insurance desk

For a hospital's insurance / TPA desk: store every patient's insurance policies, see whether each claim or pre-authorisation has **cleared**, and check whether a patient's policy is **likely eligible at this hospital** (empanelment / cashless network). A local RAG assistant answers questions **only from uploaded policy documents and recorded data** (Ollama, no paid APIs).

Backend: Python 3.11+ / FastAPI / SQLAlchemy / Alembic / PostgreSQL (or SQLite) / ChromaDB / sentence-transformers.
Frontend: React + TypeScript + Vite + Tailwind + TanStack Query + React Hook Form + Zod + Recharts.

## What it does

| Area | Notes |
|---|---|
| Hospital account | One login = one hospital (tenant). Every query is scoped to it; other hospitals' data returns 404 |
| Patients | register, search by name/MRN/phone; per-patient policies, claims, documents, records, insurance state (insured / expiring soon / expired / none) |
| Policies | belong to a patient; insurer, TPA, sum insured, validity, initial waiting days, conditions (each field tagged entered / extracted / AI-generated); masked numbers in lists |
| Hospital setup | list of empanelled insurers/TPAs (cashless on/off, valid-until). Each policy shows its network status at this hospital |
| Eligibility check | per patient and policy: validity on admission date, initial waiting period (accident exempt), network/cashless, remaining sum insured vs estimate, treatment vs recorded exclusions. Verdict: likely cashless / reimbursement route / needs review / not eligible. **Advisory only; the insurer/TPA decides** |
| Claims & pre-auth | statuses incl. pre-auth requested/approved/rejected; each maps to **Cleared / Pending / Rejected**; rejection reason and insurer reference recorded; activity timeline. **The app never contacts insurers; statuses are entered by staff** |
| Documents / records | upload per patient or policy; policy documents are indexed for the assistant |
| AI assistant | scope by patient and/or policy; deterministic answers for eligibility, claim clearance, expiry, coverage; RAG with citations for policy-wording questions |
| Reminders | auto reminders for expiring policies, missing documents, claim and pre-auth follow-up (in-app only; no email/SMS) |
| Dashboard | patients, active/expiring policies, pending/cleared/rejected claims and amounts, claims by status, attention list derived only from stored data |

### How the assistant stays honest
* Questions answerable from recorded data (expiry dates, total coverage, pending claims, claim → records, policy comparison) are answered **deterministically from the database**, labelled "as you recorded", without the LLM.
* Everything else goes through retrieval. If no chunk passes `RETRIEVAL_MIN_SCORE`, the exact message *"I couldn't find sufficient information in your uploaded documents to answer this reliably."* is returned and the LLM is **not called**.
* Citations are built from the chunks actually retrieved, never from model output.
* Uploaded text is untrusted: excerpts are delimited, instruction-like lines are stripped, and the system prompt forbids following them.
* If several policies exist and the question is ambiguous, it asks which one you mean.

## Run it

Prerequisites: Python 3.11+, Node 20+, Docker, [Ollama](https://ollama.com), Tesseract OCR (`apt install tesseract-ocr` / `brew install tesseract`).

```bash
cp .env.example .env                       # set SECRET_KEY: openssl rand -hex 32
docker compose up -d db                    # PostgreSQL 16

# Ollama (runs on the host)
ollama pull qwen2.5:7b-instruct            # or llama3.1:8b; set LLM_MODEL in .env to match
ollama serve                               # if not already running

# Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head                       # create the schema
uvicorn app.main:app --reload              # http://localhost:8000/docs
# The embedding model (BAAI/bge-small-en-v1.5) downloads from Hugging Face on first indexing.

# Frontend (new terminal)
cd frontend && npm install && npm run dev  # http://localhost:5173
```

Register your hospital, then **Settings → Load demo data**: four fictional "[DEMO]" patients, three empanelled insurers (one cashless-off), policies that are expiring / expired / outside the network, claims in every clearance state, and an indexed sample policy PDF.

Everything in containers: `docker compose up --build` (UI on :5173, API on :8000). Ollama still runs on the host.

**Calibrate retrieval once** after the first real model download: `python scripts/check_embeddings.py` prints similarity scores for relevant vs unrelated questions; set `RETRIEVAL_MIN_SCORE` between them.

### Configuration (`.env`)
`LLM_MODEL`, `EMBEDDING_MODEL`, `OLLAMA_BASE_URL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `RETRIEVAL_TOP_K`, `RETRIEVAL_MIN_SCORE`, `MAX_UPLOAD_MB`, `UPLOAD_DIR`, `CHROMA_PATH`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`. No model name is hardcoded; another local model server can be added by implementing `services/llm/base.py::LLMProvider`.

### Re-indexing
Use the refresh icon next to a policy document (or `POST /api/documents/{id}/reindex`). Old chunks and vectors are replaced, not duplicated. Changing `EMBEDDING_MODEL` requires re-indexing all documents.

## Tests

```bash
cd backend && pytest        # 65 tests, SQLite + in-memory Chroma + mock LLM; no Ollama or Postgres needed
cd frontend && npm test     # 23 tests (Vitest + Testing Library)
npm run build               # type-check + production build
```
Backend coverage includes auth, CRUD, uploads and validation, PDF/DOCX/OCR extraction, chunking, retrieval, prompt-injection handling, cross-user isolation, reminders, account deletion, and the register → login → policy → upload → index → ask → citation journey (`tests/test_e2e.py`). Tests use a deterministic hashing embedder (`EMBEDDING_PROVIDER=hash`) and a scripted LLM double; these exist only in the test suite.

## Project layout
```
backend/app/{api/routes, core, models, schemas, services/{auth,policy,claims,documents,medical_records,rag,llm,embeddings,reminders}, repositories, database, utils}
backend/{tests, alembic, scripts}      frontend/src/{components, pages, hooks→services, context, types, utils}
```

## Known limitations
* Policy fields are **not** auto-extracted from documents by the LLM; the `extracted` source tag is supported by the API but nothing sets it yet. The AI summary is generated on demand from indexed text.
* Premium-payment reminders are user-created (there is no premium-due-date field).
* Files are stored on local disk, unencrypted at rest; use disk-level encryption for real data.
* JWT is kept in `localStorage`; a production deployment should consider httpOnly cookies and rate limiting on auth endpoints.
* No email/SMS/push delivery; no insurer integration.
