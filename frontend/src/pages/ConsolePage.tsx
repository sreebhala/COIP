import { useEffect, useState } from "react";
import { api } from "../api/client";
import { AgentCard } from "../components/AgentCard";
import type {
  AppointmentRequest,
  AuditRecord,
  ReviewResult,
  WorkflowContextResponse,
  WorkflowTraceEntry,
} from "../types";

const AGENT_RESPONSIBILITY: Record<string, string> = {
  AppointmentRequestAgent:
    "Validates the request against location hours, date validity, appointment type, and contact channel.",
  ScheduleAvailabilityAgent: "Finds the requested doctor's exact slot, or a valid alternative.",
  QueueLoadAgent: "Classifies current operational queue load and estimates wait — always an estimate, never guaranteed.",
  ResourceAllocationAgent: "Recommends a configured room matching the appointment type's required room type.",
  AttendanceAndFollowUpAgent:
    "Determines confirmation need, attendance indicator, and follow-up status — operational counts only, never a clinical or behavioral judgment.",
  AppointmentOperationsDecisionAgent: "Combines all upstream evidence into the final operational decision.",
};

const AGENT_ORDER = [
  "AppointmentRequestAgent",
  "ScheduleAvailabilityAgent",
  "QueueLoadAgent",
  "ResourceAllocationAgent",
  "AttendanceAndFollowUpAgent",
  "AppointmentOperationsDecisionAgent",
];

type CardState = "pending" | "running" | "completed";

function isEmergency(result: ReviewResult): result is Extract<ReviewResult, { status: "emergency_stop" }> {
  return result.status === "emergency_stop";
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export function ConsolePage() {
  const [requests, setRequests] = useState<AppointmentRequest[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [trace, setTrace] = useState<WorkflowTraceEntry[]>([]);
  const [context, setContext] = useState<WorkflowContextResponse | null>(null);
  const [cardStates, setCardStates] = useState<Record<string, CardState>>({});
  const [auditRecord, setAuditRecord] = useState<AuditRecord | null>(null);
  const [showRawContext, setShowRawContext] = useState(false);

  useEffect(() => {
    api.appointmentRequests().then((data) => setRequests(data.items)).catch(() => undefined);
  }, []);

  const runWorkflow = async () => {
    if (!selectedCode) return;
    setRunning(true);
    setError("");
    setResult(null);
    setTrace([]);
    setContext(null);
    setAuditRecord(null);
    setCardStates(Object.fromEntries(AGENT_ORDER.map((name) => [name, "pending"])));

    try {
      const reviewResult = await api.reviewAppointment(selectedCode);
      setResult(reviewResult);

      if (isEmergency(reviewResult)) {
        setRunning(false);
        return;
      }

      const [traceData, contextData] = await Promise.all([
        api.getWorkflowTrace(reviewResult.workflow_session_id),
        api.getWorkflowContext(reviewResult.workflow_session_id),
      ]);
      setContext(contextData);

      const orderedTrace = [...traceData.agent_trace].sort((a, b) => a.sequence_number - b.sequence_number);

      // Progressive reveal: real trace data, animated as pending -> running
      // -> completed so the console demonstrates true execution order, even
      // though the backend itself is synchronous.
      for (const entry of orderedTrace) {
        setCardStates((prev) => ({ ...prev, [entry.agent_name]: "running" }));
        await sleep(420);
        setCardStates((prev) => ({ ...prev, [entry.agent_name]: "completed" }));
        setTrace((prev) => [...prev, entry]);
      }
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Workflow run failed");
    } finally {
      setRunning(false);
    }
  };

  const loadAudit = async () => {
    if (!result || isEmergency(result)) return;
    try {
      const data = await api.getAuditRecord(result.audit_reference);
      setAuditRecord(data);
    } catch {
      /* audit fetch is supplementary */
    }
  };

  const allAgentsDone = AGENT_ORDER.every((name) => cardStates[name] === "completed");
  const traceByName = Object.fromEntries(trace.map((t) => [t.agent_name, t]));

  return (
    <>
      <section className="hero-card">
        <p className="eyebrow">Stage 1.5 — Agent Workflow Console</p>
        <h2>COIP — Explainable Agentic Workflow Demo</h2>
        <p>
          This console demonstrates the full deterministic agent workflow end to end:
          domain input → shared context → agent sequence → agent outputs → final
          recommendation → explanation → audit. Every value shown is real data from
          the live backend — nothing here is scripted or invented.
        </p>
      </section>

      <section className="panel">
        <h2>Scenario / Domain Input</h2>
        <p className="panel-hint">Select an appointment request, then run the workflow.</p>
        <div className="request-grid">
          {requests.map((item) => (
            <article
              key={item.id}
              className={`request-card ${selectedCode === item.request_code ? "request-card-selected" : ""}`}
              onClick={() => setSelectedCode(item.request_code)}
              role="button"
              tabIndex={0}
            >
              <span>{item.request_code} · {item.request_source}</span>
              <h3>{item.preferred_date} at {item.preferred_time}</h3>
              <p>Confirmation: {item.confirmation_status}</p>
            </article>
          ))}
        </div>
        <button className="review-btn console-run-btn" onClick={runWorkflow} disabled={!selectedCode || running}>
          {running ? "Running Workflow…" : "Run Workflow"}
        </button>
        {error && <p className="review-error">{error}</p>}
      </section>

      {result && isEmergency(result) && (
        <section className="panel">
          <div className="review-emergency">
            <strong>Emergency workflow required.</strong>
            <p>{result.message}</p>
            <p className="review-emergency-note">
              COIP does not evaluate this request. No agent runs, no context is built
              beyond the emergency check itself, and nothing is scored or audited for
              this request. Staff must use the clinic's approved emergency process
              outside this system.
            </p>
          </div>
        </section>
      )}

      {selectedCode && !isEmergency(result ?? ({ status: "" } as ReviewResult)) && (
        <section className="panel">
          <h2>Agent Timeline &amp; Output Cards</h2>
          <div className="console-agent-grid">
            {AGENT_ORDER.map((name) => {
              const entry = traceByName[name];
              return (
                <AgentCard
                  key={name}
                  agentName={name}
                  responsibility={AGENT_RESPONSIBILITY[name]}
                  status={cardStates[name] ?? "pending"}
                  inputUsed={entry?.input_summary}
                  outputSummary={entry?.output_summary}
                  reason={entry?.rules_triggered}
                  contextUpdated={entry?.context_updated}
                  auditStatus={
                    result && !isEmergency(result) && allAgentsDone
                      ? `Recorded — ${result.audit_reference}`
                      : "Pending"
                  }
                />
              );
            })}
          </div>
        </section>
      )}

      {context && (
        <section className="panel">
          <h2>Shared Context / Workflow Memory</h2>
          <p className="panel-hint">
            Run-scoped to session <code>{context.workflow_session_id}</code> — not durable
            memory, not reused across other patients or requests.
          </p>

          {context.missing_data_flags && context.missing_data_flags.length > 0 && (
            <div className="context-missing-callout">
              <strong>Missing / incomplete data detected</strong>
              <ul>
                {context.missing_data_flags.map((flag) => (
                  <li key={flag}>{flag}</li>
                ))}
              </ul>
              <p>No value is fabricated for any missing field above.</p>
            </div>
          )}

          <div className="context-groups">
            <div className="context-group">
              <h4>Workflow Session</h4>
              <p>ID: {context.workflow_session_id}</p>
              <p>Request: {context.appointment_request_id}</p>
              <p>Status: {context.routing_status}</p>
            </div>
            <div className="context-group">
              <h4>Domain Input</h4>
              <p>Date: {String(context.appointment_request?.preferred_date ?? "—")}</p>
              <p>Time: {String(context.appointment_request?.preferred_time ?? "—")}</p>
              <p>Confirmation: {String(context.appointment_request?.confirmation_status ?? "—")}</p>
            </div>
            <div className="context-group">
              <h4>Normalized Context</h4>
              <p>Clinic: {String(context.clinic?.clinic_code ?? "—")}</p>
              <p>Location: {String(context.location?.location_code ?? "—")}</p>
              <p>Doctor: {String(context.requested_doctor?.doctor_code ?? "—")}</p>
            </div>
            <div className="context-group">
              <h4>Agent Output Memory</h4>
              {!isEmergency(result!) && result && (
                <>
                  <p>Schedule: {result.schedule.category}</p>
                  <p>Queue: {result.queue.category}</p>
                  <p>Resource: {result.resource.room_code ?? "—"}</p>
                </>
              )}
            </div>
            <div className="context-group">
              <h4>Final Result</h4>
              {!isEmergency(result!) && result && <p>{result.decision.category}</p>}
            </div>
            <div className="context-group">
              <h4>Audit Reference</h4>
              {!isEmergency(result!) && result && <p>{result.audit_reference}</p>}
            </div>
          </div>

          <button className="context-raw-toggle" onClick={() => setShowRawContext((v) => !v)}>
            {showRawContext ? "Hide" : "Show"} raw context JSON (technical view)
          </button>
          {showRawContext && <pre className="audit-box">{JSON.stringify(context, null, 2)}</pre>}
        </section>
      )}

      {result && !isEmergency(result) && allAgentsDone && (
        <section className="panel">
          <h2>Final Recommendation &amp; Explanation</h2>
          <div className={`decision-badge decision-${result.decision.category.toLowerCase().replace(/\s+/g, "-")}`}>
            {result.decision.category}
          </div>
          <div className="explanation-box">
            <span>Explanation</span>
            <p>{result.explanation}</p>
          </div>
        </section>
      )}

      {result && !isEmergency(result) && allAgentsDone && (
        <section className="panel">
          <h2>Audit Trail</h2>
          <p>Audit reference: <strong>{result.audit_reference}</strong></p>
          <button className="review-btn" onClick={loadAudit}>View Full Audit Record</button>
          {auditRecord && <pre className="audit-box">{JSON.stringify(auditRecord, null, 2)}</pre>}
        </section>
      )}

      <section className="panel">
        <h2>Known Limitations</h2>
        <ul>
          <li>Operational decision-support only — no diagnosis, clinical triage, or treatment recommendation.</li>
          <li>Alternative-doctor availability is confirmed by location/specialty match only, not a full per-doctor slot search.</li>
          <li>Room-level overlap is not tracked per room in Phase 1; "lowest load room" is approximated.</li>
          <li>Local SQLite for development; PostgreSQL is the approved production target, not yet configured.</li>
          <li>This console is a pre-cloud demo enhancement — no cloud deployment, LangGraph, or LLM is included at this stage.</li>
        </ul>
      </section>
    </>
  );
}
