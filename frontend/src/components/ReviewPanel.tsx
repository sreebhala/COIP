import { useState } from "react";
import { api } from "../api/client";
import type { AuditRecord, ReviewResult, WorkflowTraceResponse } from "../types";

type Props = {
  requestCode: string;
};

function isEmergency(result: ReviewResult): result is Extract<ReviewResult, { status: "emergency_stop" }> {
  return result.status === "emergency_stop";
}

const DECISION_CLASS: Record<string, string> = {
  "Confirm Slot": "decision-confirm",
  "Await Confirmation": "decision-await",
  "Suggest Alternative": "decision-alt",
  "Needs Review": "decision-review",
  Reject: "decision-reject",
};

export function ReviewPanel({ requestCode }: Props) {
  const [result, setResult] = useState<ReviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [trace, setTrace] = useState<WorkflowTraceResponse | null>(null);
  const [auditRecord, setAuditRecord] = useState<AuditRecord | null>(null);
  const [auditError, setAuditError] = useState("");
  const [showContext, setShowContext] = useState(false);

  const runReview = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    setTrace(null);
    setAuditRecord(null);
    try {
      const data = await api.reviewAppointment(requestCode);
      setResult(data);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "Review request failed");
    } finally {
      setLoading(false);
    }
  };

  const loadTrace = async () => {
    if (!result || isEmergency(result)) return;
    try {
      const data = await api.getWorkflowTrace(result.workflow_session_id);
      setTrace(data);
    } catch {
      /* trace is supplementary evidence; silently ignore fetch failure */
    }
  };

  const loadAudit = async () => {
    if (!result || isEmergency(result)) return;
    setAuditError("");
    try {
      const data = await api.getAuditRecord(result.audit_reference);
      setAuditRecord(data);
    } catch (reason: unknown) {
      setAuditError(reason instanceof Error ? reason.message : "Unable to load audit record");
    }
  };

  return (
    <div className="review-panel">
      <button className="review-btn" onClick={runReview} disabled={loading}>
        {loading ? "Running review…" : "Run Appointment Review"}
      </button>

      {error && (
        <div className="review-error">
          <strong>Request failed.</strong> {error}
          <p className="review-error-note">
            This is a safe failure — no appointment, doctor, or room is fabricated for an
            unknown or invalid request.
          </p>
        </div>
      )}

      {result && isEmergency(result) && (
        <div className="review-emergency">
          <strong>Emergency workflow required.</strong>
          <p>{result.message}</p>
          <p className="review-emergency-note">
            COIP does not evaluate this request. No scheduling, queue, resource, or
            attendance data is processed. Staff must use the clinic's approved emergency
            process outside this system.
          </p>
        </div>
      )}

      {result && !isEmergency(result) && (
        <div className="review-result">
          <div className={`decision-badge ${DECISION_CLASS[result.decision.category] ?? ""}`}>
            {result.decision.category}
          </div>

          <div className="review-grid">
            <div className="review-field">
              <span>Request validity</span>
              <strong>{result.request_validation.status}</strong>
            </div>
            <div className="review-field">
              <span>Doctor / slot</span>
              <strong>
                {result.schedule.category}
                {result.schedule.doctor_code ? ` · ${result.schedule.doctor_code}` : ""}
                {result.schedule.time ? ` · ${result.schedule.time}` : ""}
              </strong>
            </div>
            <div className="review-field">
              <span>Queue load</span>
              <strong>
                {result.queue.category}
                {result.queue.projected_utilization_percent !== null
                  ? ` (${result.queue.projected_utilization_percent}%)`
                  : ""}
              </strong>
              {result.queue.estimated_wait_band_minutes && (
                <p className="review-note">
                  Estimated wait: {result.queue.estimated_wait_band_minutes} minutes (estimate only, not guaranteed)
                </p>
              )}
            </div>
            <div className="review-field">
              <span>Room / resource</span>
              <strong>{result.resource.room_code ?? "Not required"}</strong>
            </div>
            <div className="review-field">
              <span>Confirmation action</span>
              <strong>{result.attendance_follow_up.confirmation_action ?? "—"}</strong>
            </div>
            <div className="review-field">
              <span>Follow-up status</span>
              <strong>{result.attendance_follow_up.follow_up_status ?? "—"}</strong>
            </div>
          </div>

          {result.reason_codes.length > 0 && (
            <div className="reason-codes">
              <span>Reason codes</span>
              <div className="reason-codes-list">
                {result.reason_codes.map((code) => (
                  <span key={code} className="reason-chip">
                    {code}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="explanation-box">
            <span>Explanation</span>
            <p>{result.explanation}</p>
          </div>

          <div className="review-actions">
            <button onClick={loadTrace}>View Agent Timeline</button>
            <button onClick={loadAudit}>View Audit Record — {result.audit_reference}</button>
            <button onClick={() => setShowContext((v) => !v)}>
              {showContext ? "Hide" : "Show"} Shared Context Fields
            </button>
          </div>

          {showContext && (
            <div className="context-note">
              Shared workflow context for this review is run-scoped to session{" "}
              <code>{result.workflow_session_id}</code> — it is not durable memory and is not
              reused across other patients or requests. Inspect the full context via{" "}
              <code>GET /api/v1/workflows/{result.workflow_session_id}/context</code>.
            </div>
          )}

          {trace && (
            <div className="agent-timeline">
              <h4>Agent Timeline</h4>
              {trace.agent_trace.map((entry) => (
                <div key={entry.sequence_number} className="timeline-entry">
                  <span className="timeline-seq">{entry.sequence_number}</span>
                  <div>
                    <strong>{entry.agent_name}</strong>
                    <p>
                      {String(entry.output_summary.classification ?? "")}
                      {entry.rules_triggered.length > 0 ? ` · ${entry.rules_triggered.join(", ")}` : ""}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {auditError && <p className="review-error">{auditError}</p>}
          {auditRecord && (
            <pre className="audit-box">{JSON.stringify(auditRecord, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
}
