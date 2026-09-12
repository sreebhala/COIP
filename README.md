# Clinic Operations Intelligence Platform (COIP)

## Repository

`COIP` — mirror of the working codebase from `RealRails-AgenticAI-COIP-Phase1`, carried forward for Stage 4 (LLM Enhancement).

## Current Status

Stage 3.1 — Conditional LangGraph Routing complete. Deterministic Agentic AI MVP (Stage 1), Agent Workflow Console visualization (Stage 1.5), cloud/Docker deployment (Stage 2), stateless LangGraph orchestration alongside the original deterministic workflow (Stage 3), and conditional route-aware LangGraph execution (Stage 3.1) are all implemented and validated. Stage 4 (LLM Enhancement) has not yet started.

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
- **LangGraph — stateless** (Stage 3) — graph orchestration layer wrapping the same existing agents as graph nodes, exposed via `POST /api/v1/graph/reviews/appointment`, alongside and validated against the original deterministic endpoint
- **LangGraph — conditional routing** (Stage 3.1) — the same graph endpoint extended with a deterministic router and 4 grounded routes: `standard`, `emergency_human_review`, `missing_configuration_review`, and `resource_not_required`. Route decision, executed path, and skipped agents are returned in the API response and recorded in the audit evidence. Frontend demo: `frontend/src/pages/ConditionalRoutingConsole.tsx` (accessible via the "Conditional Routing" sidebar link, `#conditional-routing`).

## Not Included

- Final operations dashboard (beyond the Agent Workflow Console and Conditional Routing Console)
- LLM (Stage 4 — not yet started)

## Critical Boundary

COIP is operational only. It does not diagnose, triage, interpret symptoms, recommend treatment, or store clinical notes.

This applies equally to the deterministic endpoint, the stateless LangGraph endpoint, and the conditional-routing graph — every path wraps the same underlying agents and enforces the same boundary; none of them add any new capability beyond routing/orchestration.

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

Three endpoints are available from `/docs`:
- `POST /api/v1/reviews/appointment` — original deterministic endpoint
- `POST /api/v1/graph/reviews/appointment` — LangGraph endpoint (stateless + conditional routing, same endpoint, additive response fields)
- `GET /api/v1/audit/{audit_reference}` — audit retrieval, including route decisions

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Sidebar links: Dashboard, Appointment Requests, Safety Boundary, Agent Workflow Console, Conditional Routing.

## Docker

```bash
docker compose up --build
```

## Tests

```bash
cd backend
pytest
```

63 tests total: the original deterministic-workflow suite, `test_graph_comparison.py` (Stage 3 old-vs-graph validation), and `test_conditional_routing.py` (Stage 3.1, covering all 4 routes plus a comparability check proving the resource-skip route produces an identical decision to the legacy endpoint).

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
