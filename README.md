# FinSight AI — Agentic Financial Document Processing Platform

[![Backend CI / Pytest](https://img.shields.io/badge/pytest-27%20passed-emerald.svg)](https://github.com)
[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![React Version](https://img.shields.io/badge/react-18-blue.svg)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2+-purple.svg)](https://github.com/langchain-ai/langgraph)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**FinSight AI** is an enterprise-grade, agentic AI invoice processing and financial reconciliation platform designed for corporate finance and accounts payable (AP) teams.

Unlike brittle rule engines or toy LLM wrappers, FinSight AI implements a robust **modular monolith** combining **FastAPI**, **LangGraph** with persistent MongoDB state checkpointing, **Google Gemini 2.5 Flash** for structured extraction, **Celery + Redis distributed locks** for idempotent background execution, and a responsive **React + TypeScript + Tailwind CSS** dashboard featuring a real-time Human-in-the-Loop (HITL) review queue.

---

## Architecture Overview

```
                                  +---------------------------------------------+
                                  |            React 18 + Vite SPA              |
                                  |  (Dashboard, Review Queue, Invoice Viewer)  |
                                  +---------------------------------------------+
                                                         |
                                                  HTTP / REST (JWT)
                                                         v
                                  +---------------------------------------------+
                                  |            FastAPI API Gateway              |
                                  |   (Auth, File Validation, Lifecycle REST)  |
                                  +---------------------------------------------+
                                        /                                 \
                       Job Dispatch    /                                   \ Read / Resume
                                      v                                     v
                  +-----------------------+                         +---------------------+
                  |   Redis 7 Task Broker |                         |  MongoDB Database   |
                  |  + Distributed Locks  |                         |  - invoices         |
                  +-----------------------+                         |  - users            |
                              |                                     |  - audit_logs       |
                              v                                     |  - checkpoints      |
                  +-----------------------+                         +---------------------+
                  | Celery Async Workers  |                                    ^
                  +-----------------------+                                    |
                              |                                                |
                              +--------> Runs LangGraph State Machine ---------+
```

### The 9-Node LangGraph State Machine

```mermaid
flowchart TD
    Start([Upload Invoice]) --> DL[1. document_loader]
    DL --> TE[2. text_extractor]
    TE --> IE[3. invoice_extractor\n(Gemini 2.5 Flash)]
    IE --> V[4. validator\n(Deterministic Math & Schema)]
    
    V -->|Validation Failed & Retries < 2| IE
    V -->|Validated or Retries Exhausted| DC[5. duplicate_checker\n(SHA-256 + Vendor/Inv Key)]
    
    DC --> RA[6. risk_assessor\n(Additive Risk Scoring)]
    
    RA -->|Risk < 0.40 & No Errors| F[8. finalizer\n(Status: APPROVED)]
    RA -->|Risk >= 0.40 or Duplicate| HR[7. human_review\n(interrupt: Paused)]
    
    HR -->|Command: Resume & Adjudicate| F
    
    DL -.->|File / Format Error| EH[9. error_handler\n(Status: FAILED)]
    TE -.->|Scanned / Non-text Error| EH
    
    F --> End([Complete])
    EH --> End
```

---

## Key Technical Highlights (Why This Architecture Stands Out)

1. **Stateful Agent Orchestration with LangGraph Checkpointing**:
   - Rather than executing LLM calls in stateless loops, the pipeline uses a compiled `StateGraph` backed by `MongoDBSaver`.
   - When an invoice triggers risk thresholds (e.g., GST calculation mismatches, duplicate vendor hashes, or low model confidence), the graph triggers `interrupt({"reason": ...})` and yields execution safely.
   - When a human reviewer approves or submits corrections via the UI, the backend invokes `graph.invoke(Command(resume=corrections), config=...)`, resuming execution precisely at the paused checkpoint.

2. **Strict Financial Calculations & Deterministic Validation**:
   - LLMs can hallucinate math. FinSight AI never trusts LLM-calculated sums.
   - A dedicated Python validator node verifies `subtotal + CGST + SGST + IGST == grand_total` using `Decimal` fixed-point arithmetic (avoiding IEEE 754 float rounding errors).
   - Validates Indian GSTIN formats with exact state-code and checksum regular expressions (`^\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d]Z[A-Z\d]$`).

3. **Production Idempotency & Distributed Locking**:
   - Background tasks run in Celery workers protected by atomic Redis distributed locks (`finsight:lock:invoice:{id}`).
   - Double-clicking upload or network retries will not spawn duplicate LLM calls or corrupt database states.
   - Terminal states (`APPROVED`, `REJECTED`, `FAILED`) are enforced atomically in MongoDB using optimistic concurrency filters (`status: {"$in": ["PROCESSING", "REVIEW_REQUIRED"]}`).

4. **Multi-Tenant Data Isolation**:
   - Every invoice, duplicate search query, checkpoint, and audit log entry is partitioned by `user_id`.
   - Cross-tenant data leakage is prevented at both the database query level and API middleware.

5. **Pure Digital PDF Extraction (No Unreliable OCR Dependencies)**:
   - Built with high-performance `PyMuPDF (fitz)` for direct vector and text-layer extraction.
   - Unparseable, scanned, or image-only PDFs are intercepted early with clear user feedback rather than silently feeding garbage or empty tokens to Gemini.

---

## Tech Stack

| Domain | Technology | Purpose |
|---|---|---|
| **Backend** | Python 3.11, FastAPI, Pydantic v2 | High-throughput asynchronous REST API |
| **Agentic AI** | LangGraph 1.2+, Google Gemini 2.5 Flash | Structured JSON extraction & stateful HITL workflow |
| **Database** | MongoDB 7.0, Motor, PyMongo | Document persistence & LangGraph checkpoint storage |
| **Job Queue** | Celery 5.4, Redis 7 | Asynchronous document ingestion with distributed locking |
| **Document Processing**| PyMuPDF (fitz) | Fast, deterministic digital PDF text extraction |
| **Observability** | Langfuse v3 | Tracing model latency, token consumption, and errors |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS | Responsive, accessible finance analyst dashboard |
| **UI Components** | Lucide React, Recharts | Interactive charts and status visualization |
| **Containerization**| Docker, Docker Compose, Nginx | Multi-stage production container deployment |

---

## Repository Structure

```
FinSight AI/
├── .github/workflows/
│   └── ci.yml                     # Automated GitHub Actions test & build pipeline
├── backend/
│   ├── app/
│   │   ├── agents/                # LangGraph state machine & nodes
│   │   │   ├── nodes/             # document_loader, text_extractor, invoice_extractor,
│   │   │   │                      # validator, duplicate_checker, risk_assessor,
│   │   │   │                      # human_review, finalizer, error_handler
│   │   │   ├── prompts/           # Specialized extraction system prompts
│   │   │   ├── checkpointer.py    # MongoDBSaver checkpoint integration
│   │   │   ├── graph.py           # Compiled LangGraph workflow
│   │   │   └── state.py           # TypedDict schema for pipeline state
│   │   ├── auth/                  # JWT auth, bcrypt hashing, dependencies
│   │   ├── dashboard/             # Aggregation pipelines for analytics
│   │   ├── invoices/              # Invoice CRUD, file streaming, audit trails
│   │   ├── schemas/               # Strict Pydantic models (Decimal, LineItems)
│   │   ├── services/              # PDF processor, file storage, Langfuse client
│   │   ├── utils/                 # Logging, HTTP exception handlers
│   │   ├── workers/               # Celery app and distributed async tasks
│   │   ├── config.py              # Pydantic Settings with production validation
│   │   ├── database.py            # Event-loop-aware MongoDB client singleton
│   │   └── main.py                # FastAPI application entrypoint
│   ├── tests/                     # 27 comprehensive unit & integration tests
│   ├── Dockerfile                 # Multi-stage Python 3.11 production image
│   ├── pytest.ini                 # Pytest asyncio configuration
│   └── requirements.txt           # Fully resolved, conflict-free dependencies
├── frontend/
│   ├── src/
│   │   ├── api/                   # Axios client with auth interceptors
│   │   ├── components/
│   │   │   ├── invoice/           # StatusBadge, RiskBadge, UploadZone
│   │   │   └── layout/            # Sidebar, AppShell navigation
│   │   ├── pages/
│   │   │   ├── auth/              # LoginPage, RegisterPage
│   │   │   ├── DashboardPage.tsx  # KPI cards, Recharts pie chart, activity feed
│   │   │   ├── InvoicesPage.tsx   # Search, status filters, paginated table
│   │   │   ├── InvoiceDetailPage.tsx # Split view: PDF preview + field editor
│   │   │   └── ReviewQueuePage.tsx   # Master-detail human review queue
│   │   ├── stores/                # Zustand authStore with localStorage sync
│   │   ├── types/                 # TypeScript interfaces
│   │   ├── App.tsx                # React Router v6 protected routing
│   │   └── main.tsx               # Entrypoint with TanStack Query provider
│   ├── nginx.conf                 # Production Nginx reverse-proxy configuration
│   └── Dockerfile                 # Multi-stage Node builder + Nginx alpine
├── docker-compose.yml             # Full-stack composition (API, Worker, UI, Mongo, Redis)
└── README.md
```

---

## Getting Started

### Prerequisites

- **Docker & Docker Compose** (Recommended for full stack), OR:
- **Python 3.11+**, **Node.js 20+**, **MongoDB 7+**, and **Redis 7+** installed locally.
- A **Google Gemini API Key** ([Google AI Studio](https://aistudio.google.com/)).

---

### Option 1: Run with Docker Compose (Fastest)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/finsight-ai.git
   cd finsight-ai
   ```

2. **Configure Environment Variables**:
   Copy the sample environment file:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your Gemini API key:
   ```env
   GOOGLE_API_KEY=your_actual_gemini_api_key
   SECRET_KEY=generate_a_random_32_char_secret_key
   ```

3. **Start the Application**:
   ```bash
   docker compose up --build
   ```

4. **Access the Application**:
   - **Web UI**: [http://localhost](http://localhost)
   - **Backend API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **API Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Option 2: Local Development Setup

#### 1. Start MongoDB and Redis
Using Docker for the database dependencies:
```bash
docker run -d --name mongo -p 27017:27017 mongo:7
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

#### 2. Backend Setup
```bash
cd backend

# Create and activate Python 3.11 virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

In a separate terminal, start the **Celery worker**:
```bash
cd backend
# On Windows (use gevent or solo pool for local dev):
celery -A app.workers.celery_app worker --loglevel=info -P solo
# On Linux/macOS:
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
```

#### 3. Frontend Setup
```bash
cd frontend

# Install packages
npm install

# Start Vite dev server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Running the Automated Test Suite

The test suite covers schema validation, PDF extraction, GST business calculations, duplicate detection algorithms, JWT authentication, LangGraph state transitions, human review resumption, and API endpoints:

```bash
cd backend
pytest -v --tb=short
```

Expected output:
```
tests/test_auth.py::test_user_registration_and_login PASSED              [  3%]
tests/test_auth.py::test_protected_route_without_token PASSED            [  7%]
tests/test_business_validation.py::test_business_validation_valid_invoice PASSED [ 11%]
tests/test_business_validation.py::test_business_validation_detects_math_mismatch PASSED [ 14%]
tests/test_business_validation.py::test_business_validation_detects_due_date_before_invoice_date PASSED [ 18%]
tests/test_celery_idempotency.py::test_redis_distributed_locking_prevents_concurrent_runs PASSED [ 22%]
tests/test_celery_idempotency.py::test_terminal_job_is_skipped PASSED    [ 25%]
tests/test_duplicate_detection.py::test_duplicate_file_hash_detection PASSED [ 29%]
tests/test_duplicate_detection.py::test_duplicate_vendor_invoice_number_detection PASSED [ 33%]
tests/test_duplicate_detection.py::test_tenant_isolation_duplicate_checking PASSED [ 37%]
tests/test_human_review.py::test_human_review_interrupt_and_resumption PASSED [ 40%]
tests/test_invoice_schema.py::test_extracted_invoice_valid_gstin PASSED  [ 44%]
tests/test_invoice_schema.py::test_extracted_invoice_invalid_gstin_returns_none PASSED [ 48%]
tests/test_invoice_schema.py::test_decimal_precision_preservation PASSED [ 51%]
tests/test_invoice_schema.py::test_line_item_validation PASSED           [ 55%]
tests/test_invoice_schema.py::test_model_dump_json_compatibility PASSED  [ 59%]
tests/test_invoices_api.py::test_invoice_upload_and_lifecycle_api PASSED [ 62%]
tests/test_invoices_api.py::test_invoice_approval_and_rejection_api PASSED [ 66%]
tests/test_invoices_api.py::test_dashboard_stats_and_activity_api PASSED [ 70%]
tests/test_invoices_api.py::test_tenant_isolation_on_api PASSED          [ 74%]
tests/test_langgraph_routing.py::test_routing_functions PASSED           [ 77%]
tests/test_langgraph_routing.py::test_end_to_end_graph_auto_approval PASSED [ 81%]
tests/test_pdf_extraction.py::test_extract_text_valid_pdf PASSED         [ 85%]
tests/test_pdf_extraction.py::test_reject_empty_or_scanned_pdf PASSED    [ 88%]
tests/test_pdf_extraction.py::test_file_not_found_handling PASSED        [ 92%]
tests/test_status_transitions.py::test_atomic_status_transition_success PASSED [ 96%]
tests/test_status_transitions.py::test_atomic_status_transition_prevents_duplicate_approval PASSED [100%]

============================= 27 passed in 4.01s ==============================
```

To build and typecheck the frontend:
```bash
cd frontend
npm run build
```

---

## API Reference (v1)

### Authentication
- `POST /api/v1/auth/register` — Register a new organization user.
- `POST /api/v1/auth/login` — Authenticate and receive a Bearer JWT.
- `GET /api/v1/auth/me` — Retrieve the currently authenticated user profile.

### Invoice Processing
- `POST /api/v1/invoices/upload` — Upload an invoice PDF (triggers background Celery task).
- `GET /api/v1/invoices` — List invoices with pagination, status filters, and search.
- `GET /api/v1/invoices/{id}` — Get invoice detail, risk breakdown, and line items.
- `GET /api/v1/invoices/{id}/status` — Poll current workflow status and risk score.
- `GET /api/v1/invoices/{id}/file` — Stream authenticated source PDF for preview.
- `PATCH /api/v1/invoices/{id}` — Edit extracted fields prior to approval.
- `POST /api/v1/invoices/{id}/approve` — Approve invoice and resume LangGraph workflow.
- `POST /api/v1/invoices/{id}/reject` — Reject invoice with reviewer remarks.
- `POST /api/v1/invoices/{id}/retry` — Re-queue a failed invoice execution.
- `GET /api/v1/invoices/{id}/audit` — Retrieve immutable audit trail of workflow events.

### Analytics & Dashboard
- `GET /api/v1/dashboard/stats` — Total count, approved value, and pipeline status breakdown.
- `GET /api/v1/dashboard/recent-activity` — Recent real-time audit feed across documents.

---

## Placement & Interview Talking Points

When discussing this project in engineering interviews:

1. **Why LangGraph instead of a simple linear Python script?**
   - *Answer:* Real document extraction is non-linear and stateful. We need conditional loops (retrying extraction with targeted hints if validation fails), deterministic branching, and checkpointing for human review. LangGraph provides durable persistence via `MongoDBSaver`, so a long-running graph can pause for hours waiting for human approval without holding memory or worker processes.

2. **How did you handle Celery worker and FastAPI event loop conflicts with MongoDB?**
   - *Answer:* Motor’s `AsyncIOMotorClient` binds to the event loop on creation. In Celery workers using `asgiref.sync.async_to_sync`, different tasks execute in different event loops, which triggers `RuntimeError: Event loop is closed`. I solved this by implementing a loop-aware client manager in `database.py` that tracks `asyncio.get_running_loop()` and provisions clean client instances per loop lifecycle.

3. **Why Decimal instead of Float for invoice numbers?**
   - *Answer:* Standard IEEE-754 floating-point numbers cannot accurately represent base-10 fractions (e.g. `0.1 + 0.2 != 0.3`). In financial systems, accumulating rounding errors results in audit failure. All tax and total calculations use `Decimal` with deterministic precision checks.

4. **How is idempotency enforced?**
   - *Answer:* Through a two-tiered defense: (1) Redis distributed locks prevent concurrent Celery tasks from operating on the same invoice ID, and (2) atomic MongoDB update operators with status preconditions (`status: {"$in": ["PROCESSING", "REVIEW_REQUIRED"]}`) prevent double approvals or race conditions.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
