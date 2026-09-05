# Clinic Operations Intelligence Platform (COIP)

## Repository

`RealRails-AgenticAI-COIP-Phase1`

## Current Status

Stage 3 — LangGraph Stateless complete. Deterministic Agentic AI MVP (Stage 1), Agent Workflow Console visualization (Stage 1.5), cloud/Docker deployment (Stage 2), and a stateless LangGraph orchestration layer alongside the original deterministic workflow (Stage 3) are all implemented and validated.

## Included

- FastAPI
- SQLAlchemy
- PostgreSQL configuration
- SQLite local fallback
- Clinic/location, doctors, availability, appointment types, rooms, requests, appointments, queues, attendance, and follow-up foundations
- Appointment-request APIs
- Seed loader
- React + Vite + TypeScript shell
- Base AgentOutput
- WorkflowSession
- AgentExecutionLog
- DecisionRecord
- Docker readiness
- **Context Builder** (`services/context/context_builder.py`) — builds `SharedWorkflowContext` per run, including the emergency-stop and missing-configuration safety checks
- **Operational agents** (`services/agents/`) — `AppointmentRequestAgent`, `ScheduleAvailabilityAgent`, `QueueLoadAgent`, `ResourceAllocationAgent`, `AttendanceAndFollowUpAgent`, `AppointmentOperationsDecisionAgent`
- **Rule engine** (`services/rules/`) — rule catalogue backing agent classifications
- **Orchestrator** (`services/orchestrators/appointment_review_orchestrator.py`) — runs the deterministic agent sequence end to end
- **Final appointment recommendation** — decision + schedule + queue + resource + attendance/follow-up + reason codes, returned from `POST /api/v1/reviews/appointment`
- **Audit retrieval** — `GET /api/v1/audit/{audit_reference}`, backed by `DecisionRecord`
- **Agent Workflow Console** (Stage 1.5) — `frontend/src/pages/ConsolePage.tsx`, animates real agent execution from live backend data
- **LangGraph** (Stage 3) — stateless graph orchestration layer wrapping the same existing agents as graph nodes, exposed via `POST /api/v1/graph/reviews/appointment`, alongside and validated against the original deterministic endpoint. See `STAGE3_INTEGRATION_README.md` for details.

## Not Included

- Final operations dashboard (beyond the Agent Workflow Console)
- LLM (planned for Stage 4)
- Conditional/route-aware LangGraph execution (planned for Stage 3.1, in progress)

## Critical Boundary

COIP is operational only. It does not diagnose, triage, interpret symptoms, recommend treatment, or store clinical notes.

This applies equally to both the deterministic endpoint and the LangGraph endpoint — the graph layer wraps the same agents and enforces the same boundary, it does not add any new capability.

## Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m app.data.seed
uvicorn app.main:app --reload --port 8000
```

Open:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

Both the deterministic endpoint (`POST /api/v1/reviews/appointment`) and the LangGraph endpoint (`POST /api/v1/graph/reviews/appointment`) are available from `/docs`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Docker

```bash
docker compose up --build
```

## Tests

```bash
cd backend
pytest
```

Includes the original deterministic-workflow test suite plus `test_graph_comparison.py`, which validates the LangGraph endpoint against the deterministic endpoint for matching input.

## Phase 1 Sequence

1. Product, Domain and Architecture Readiness
2. Application Foundation and Domain Data
3. Context Builder and Shared Workflow Context
4. Deterministic Agents and Rule Engine
5. Orchestration, Recommendation and Audit
6. Dashboard, Validation and Handover

## Stage Progress

| Stage | Description | Status |
|---|---|---|
| 1 | Deterministic Agentic AI MVP | Complete |
| 1.5 | Agent Workflow Visualization (Agent Workflow Console) | Complete |
| 2 | Cloud/Docker Deployment | Complete |
| 3 | LangGraph Stateless (graph layer alongside deterministic workflow) | Complete |
| 3.1 | Conditional LangGraph Routing | Complete |
| 4 | LLM Enhancement | Not started |
