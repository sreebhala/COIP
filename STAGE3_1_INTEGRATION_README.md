# Stage 3.1 — Conditional LangGraph Routing — Integration Guide

## Files to replace (Stage 3 files, updated for Stage 3.1)

```
backend/app/application/graphs/workflow_state.py
backend/app/application/graphs/workflow_graph.py
backend/app/application/graphs/graph_runner.py
backend/app/application/graphs/nodes/explanation_audit_node.py
```

## Files to add (new)

```
backend/app/application/graphs/nodes/router_node.py
backend/app/application/graphs/nodes/resource_skip_node.py
backend/tests/test_conditional_routing.py
frontend/src/pages/ConditionalRoutingConsole.tsx
```

## seed.py — 3 manual edits required

See `SEED_PATCH_INSTRUCTIONS.md` in this package. REQ-006 and REQ-007
are new fixtures needed to demonstrate 2 of the 4 routes end-to-end —
neither existing route condition was exercised by REQ-001..REQ-005.

## Frontend wiring

`ConditionalRoutingConsole.tsx` is self-contained (own fetch, own state,
inline styles) and does not modify `ConsolePage.tsx`. Add a route/nav
entry to mount it, e.g. in your router:

```tsx
import ConditionalRoutingConsole from "./pages/ConditionalRoutingConsole";
// <Route path="/conditional-routing" element={<ConditionalRoutingConsole />} />
```

And a sidebar link next to "Agent Workflow Console", pointing at that
route.

## Design decisions made (per the Post 5 discovery comment)

- **4 routes, not 5** — COIP has no priority/SLA/compliance field, so
  those generic-template routes were not invented.
- **missing_configuration = Option A (labeled, not skipped)** — all 6
  agents still run; only the route label/reason differ. Zero risk to
  legacy-endpoint comparability for this case.
- **resource_not_required = real skip** — `ResourceAllocationAgent`'s
  output is 100% deterministic from one field, so `resource_skip_node`
  synthesizes the exact same output rather than calling the agent.
  `test_resource_skip_matches_legacy_endpoint_output` proves the final
  decision is identical to the legacy endpoint's for the same input.
- **Same endpoint, not a new one** — `POST /api/v1/graph/reviews/appointment`
  was extended in place rather than adding a second endpoint.
  `graph_mode` deliberately stays `"langgraph_stateless"` (unchanged) —
  a new `"conditional_routing": true` field marks routing as active,
  rather than renaming `graph_mode` to `"conditional_langgraph"`, so the
  existing Stage 3 old-vs-graph comparison tests keep passing unchanged.
- **Route decision is audited** — `explanation_audit_node.py` adds a
  `"routing"` key to `evidence_snapshot`, retrievable via
  `GET /api/v1/audit/{audit_reference}`.

## Local run steps

```powershell
cd backend
python -m app.data.seed
uvicorn app.main:app --reload --port 8000
```

```powershell
cd backend
python -m pytest -v
```

Expect the existing 56 tests plus 7 new ones in
`test_conditional_routing.py` = **63 total**.

## Manual scenario verification (via /docs)

| Scenario | Request ID | Expected `selected_route` |
|---|---|---|
| Standard | REQ-001 | `standard` |
| Emergency | REQ-005 | `emergency_human_review` |
| Missing configuration | REQ-006 | `missing_configuration_review` |
| Resource not required | REQ-007 | `resource_not_required` |

## What was deliberately NOT done

- No LLM.
- No new priority/SLA/compliance fields invented.
- No change to any existing agent's business logic.
- No change to the legacy deterministic endpoint.
- No renaming of the Stage 3 graph endpoint's existing response fields —
  only additive fields were introduced.
