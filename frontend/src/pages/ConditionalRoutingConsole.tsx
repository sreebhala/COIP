/**
 * Conditional LangGraph Routing Console — Stage 3.1
 *
 * Self-contained page: its own scenario selector, its own fetch call to
 * the (Stage 3.1-extended) graph endpoint, its own rendering. Built this
 * way deliberately so it does not depend on internals of the existing
 * Stage 1.5 ConsolePage.tsx and cannot break it — add a route/nav entry
 * to mount this alongside it, nothing in ConsolePage.tsx needs to change.
 *
 * Known limitation shown in the UI, matching the rest of the app: this is
 * a deterministic conditional-routing demo, not autonomous production AI.
 */
import { useState } from "react";

type Scenario = {
  id: string;
  label: string;
  description: string;
};

const SCENARIOS: Scenario[] = [
  { id: "REQ-001", label: "REQ-001 · Standard", description: "Complete case, no exception trigger." },
  { id: "REQ-005", label: "REQ-005 · Emergency", description: "Emergency flag entered by staff." },
  { id: "REQ-006", label: "REQ-006 · Missing Configuration", description: "Requested doctor has no configured availability." },
  { id: "REQ-007", label: "REQ-007 · Resource Not Required", description: "Appointment type has no required room type." },
];

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

type GraphResponse = {
  status?: string;
  selected_route?: string;
  route_reason?: string;
  route_flags?: Record<string, boolean>;
  executed_path?: string[];
  skipped_agents?: { agent: string; reason: string }[];
  agent_trace?: { agent: string; classification: string; rules_triggered: string[] }[];
  shared_state?: Record<string, unknown>;
  final_output?: Record<string, unknown>;
  audit_reference?: string | null;
  message?: string;
  [key: string]: unknown;
};

export default function ConditionalRoutingConsole() {
  const [selectedScenario, setSelectedScenario] = useState<string>(SCENARIOS[0].id);
  const [result, setResult] = useState<GraphResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runConditionalGraph() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(`${API_BASE}/api/v1/graph/reviews/appointment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ appointment_request_id: selectedScenario }),
      });
      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail ?? `Request failed (${response.status})`);
      }
      const body: GraphResponse = await response.json();
      setResult(body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "24px", fontFamily: "system-ui, sans-serif" }}>
      <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1, color: "#1e3a8a", marginBottom: 4 }}>
        STAGE 3.1 — CONDITIONAL LANGGRAPH ROUTING
      </div>
      <h1 style={{ fontSize: 26, fontWeight: 700, marginBottom: 8 }}>COIP — Conditional Routing Demo</h1>
      <p style={{ color: "#475569", marginBottom: 24 }}>
        Different appointment requests travel through different LangGraph paths.
        Select a scenario, run it, and see exactly which route was selected, why,
        which nodes executed, and which were skipped.
      </p>

      <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, marginBottom: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>Scenario Selector</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
          {SCENARIOS.map((scenario) => (
            <button
              key={scenario.id}
              onClick={() => setSelectedScenario(scenario.id)}
              style={{
                textAlign: "left",
                padding: 14,
                borderRadius: 10,
                border: selectedScenario === scenario.id ? "2px solid #1e3a8a" : "1px solid #e2e8f0",
                background: selectedScenario === scenario.id ? "#eff6ff" : "#fff",
                cursor: "pointer",
              }}
            >
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{scenario.label}</div>
              <div style={{ fontSize: 13, color: "#64748b" }}>{scenario.description}</div>
            </button>
          ))}
        </div>
        <button
          onClick={runConditionalGraph}
          disabled={loading}
          style={{
            marginTop: 16,
            padding: "10px 20px",
            borderRadius: 8,
            border: "none",
            background: "#1e3a8a",
            color: "#fff",
            fontWeight: 600,
            cursor: loading ? "default" : "pointer",
            opacity: loading ? 0.6 : 1,
          }}
        >
          {loading ? "Running..." : "Run Conditional Graph"}
        </button>
        {error && <div style={{ marginTop: 12, color: "#b91c1c" }}>{error}</div>}
      </div>

      {result && (
        <>
          <Panel title="Selected Route">
            <div style={{ fontSize: 18, fontWeight: 700, color: "#1e3a8a" }}>
              {result.selected_route ?? "—"}
            </div>
          </Panel>

          <Panel title="Route Reason">
            <p style={{ color: "#334155" }}>{result.route_reason ?? "—"}</p>
          </Panel>

          <Panel title="Route Flags">
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {result.route_flags &&
                Object.entries(result.route_flags).map(([flag, value]) => (
                  <span
                    key={flag}
                    style={{
                      padding: "4px 10px",
                      borderRadius: 999,
                      fontSize: 12,
                      fontWeight: 600,
                      background: value ? "#fef3c7" : "#f1f5f9",
                      color: value ? "#92400e" : "#64748b",
                    }}
                  >
                    {flag}: {String(value)}
                  </span>
                ))}
            </div>
          </Panel>

          <Panel title="Executed Graph Path">
            <ol style={{ paddingLeft: 20 }}>
              {(result.executed_path ?? []).map((node, i) => (
                <li key={i} style={{ marginBottom: 4, fontFamily: "monospace", fontSize: 13 }}>
                  {node}
                </li>
              ))}
            </ol>
          </Panel>

          <Panel title="Skipped Agents">
            {(result.skipped_agents ?? []).length === 0 ? (
              <p style={{ color: "#64748b" }}>None — every agent ran.</p>
            ) : (
              (result.skipped_agents ?? []).map((skip, i) => (
                <div key={i} style={{ marginBottom: 10, paddingLeft: 12, borderLeft: "3px solid #fca5a5" }}>
                  <div style={{ fontWeight: 600 }}>{skip.agent}</div>
                  <div style={{ fontSize: 13, color: "#64748b" }}>{skip.reason}</div>
                </div>
              ))
            )}
          </Panel>

          {result.agent_trace && (
            <Panel title="Agent Output Cards">
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
                {result.agent_trace.map((agent, i) => (
                  <div key={i} style={{ border: "1px solid #e2e8f0", borderRadius: 8, padding: 12 }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{agent.agent}</div>
                    <div style={{ fontSize: 13, color: "#1e3a8a", marginTop: 4 }}>{agent.classification}</div>
                    <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>
                      {(agent.rules_triggered ?? []).join(", ")}
                    </div>
                  </div>
                ))}
              </div>
            </Panel>
          )}

          <Panel title="Final Recommendation">
            <pre style={{ background: "#f8fafc", padding: 12, borderRadius: 8, fontSize: 12, overflowX: "auto" }}>
              {JSON.stringify(result.final_output ?? result.message ?? {}, null, 2)}
            </pre>
          </Panel>

          <Panel title="Shared Context">
            <pre style={{ background: "#f8fafc", padding: 12, borderRadius: 8, fontSize: 12, overflowX: "auto", maxHeight: 220 }}>
              {JSON.stringify(result.shared_state ?? {}, null, 2)}
            </pre>
          </Panel>

          <Panel title="Audit Reference">
            <p style={{ fontFamily: "monospace" }}>{result.audit_reference ?? "None (emergency-stop cases are not audited)"}</p>
          </Panel>

          <Panel title="Known Limitations">
            <p style={{ fontSize: 13, color: "#64748b" }}>
              Operational decision-support only — no diagnosis, clinical triage, or
              treatment recommendation. This is a deterministic conditional LangGraph
              evolution of the Agentic AI MVP, not autonomous production AI.
            </p>
          </Panel>
        </>
      )}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: 20, marginBottom: 16 }}>
      <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10, color: "#1e3a8a" }}>{title}</h3>
      {children}
    </div>
  );
}
