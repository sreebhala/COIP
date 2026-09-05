# Stage 3 — LangGraph Stateless — Integration Guide

## 1. Files to add (new)

Copy these into your repo at the same relative paths:

```
backend/app/application/__init__.py
backend/app/application/graphs/__init__.py
backend/app/application/graphs/workflow_state.py
backend/app/application/graphs/workflow_graph.py
backend/app/application/graphs/graph_runner.py
backend/app/application/graphs/nodes/__init__.py
backend/app/application/graphs/nodes/_common.py
backend/app/application/graphs/nodes/context_node.py
backend/app/application/graphs/nodes/appointment_request_node.py
backend/app/application/graphs/nodes/schedule_availability_node.py
backend/app/application/graphs/nodes/queue_load_node.py
backend/app/application/graphs/nodes/resource_allocation_node.py
backend/app/application/graphs/nodes/attendance_follow_up_node.py
backend/app/application/graphs/nodes/decision_node.py
backend/app/application/graphs/nodes/explanation_audit_node.py
backend/app/api/routes/graph_reviews.py
backend/tests/test_graph_comparison.py
```

## 2. Files to change (existing)

- `backend/app/api/router.py` — one new import + one new `include_router` line for `graph_reviews`. Full replacement file included here for convenience; nothing else in it changed.
- `backend/requirements.txt` — one new line: `langgraph==0.6.7`. Full file included here for convenience.

Everything else in your repo — every agent, the context builder, the rule engine, the orchestrator, explanation/audit services, the existing `/api/v1/reviews/appointment` endpoint, and the frontend console — is untouched.

## 3. Local run steps

```bash
cd backend
pip install -r requirements.txt   # picks up langgraph
python -m app.data.seed           # if not already seeded
uvicorn app.main:app --reload --port 8000
```

Check both endpoints exist:
- `http://localhost:8000/docs` → confirm `POST /api/v1/reviews/appointment` (existing) and `POST /api/v1/graph/reviews/appointment` (new) both appear.

## 4. Old vs graph comparison steps

```bash
cd backend
pytest tests/test_orchestrator.py tests/test_graph_comparison.py -v
```

Or manually:

```bash
curl -X POST http://localhost:8000/api/v1/reviews/appointment \
  -H "Content-Type: application/json" \
  -d '{"appointment_request_id": "REQ-001"}'

curl -X POST http://localhost:8000/api/v1/graph/reviews/appointment \
  -H "Content-Type: application/json" \
  -d '{"appointment_request_id": "REQ-001"}'
```

Compare `decision.category`, `schedule.category`, `resource.room_code`, `reason_codes` (sorted), and the agent names in `agent_trace` — these must match. `workflow_session_id`/`workflow_id` and `audit_reference` will legitimately differ (new session per call), same as calling the deterministic endpoint twice.

## 5. Evidence checklist

| Item | How to capture |
|---|---|
| Both endpoints visible in `/docs` | Screenshot |
| `pytest` full suite green, including `test_graph_comparison.py` | Terminal output |
| Manual curl comparison for REQ-001 (normal) and REQ-005 (emergency) | Terminal output / saved JSON |
| Existing Stage 1.5 Agent Workflow Console still works unchanged | Screenshot (console still calls `/api/v1/reviews/appointment` — no frontend change was made) |
| Docker Compose still builds/starts with the new dependency | `docker compose up --build` output |

## 6. What was deliberately NOT done

- No LLM anywhere.
- No agent business logic was rewritten — every node calls the existing agent class's `.run()` unchanged.
- No existing endpoint, model, or table was removed or altered.
- No LangGraph checkpointing/persistence — `WorkflowSession`, `AgentExecutionLog`, `DecisionRecord` remain the durable state, exactly as before.
- Frontend untouched — Stage 1.5 console keeps using the deterministic endpoint; wiring it to the graph endpoint (if desired) is a Stage 3 follow-up choice, not required for this stage.
