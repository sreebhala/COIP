import { useEffect, useState } from "react";
import { api } from "../api/client";
import { ReviewPanel } from "../components/ReviewPanel";
import type { AppointmentRequest } from "../types";

export function DashboardPage() {
  const [requests, setRequests] = useState<AppointmentRequest[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);

  useEffect(() => {
    api.appointmentRequests()
      .then((data) => setRequests(data.items))
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load appointment requests"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <section id="dashboard" className="hero-card">
        <p className="eyebrow">Phase 1 — Deterministic Clinic Operations Intelligence</p>
        <h2>Appointment operations review</h2>
        <p>
          Select an appointment request below and run a review to see the full
          deterministic workflow: schedule availability, queue load, resource
          allocation, confirmation/follow-up status, the final operational
          decision, agent timeline, explanation, and audit evidence — all
          computed live from real backend data.
        </p>
      </section>

      <section className="safety-banner">
        <strong>Operational scope only.</strong>
        <span>No diagnosis, clinical triage, symptom analysis, or treatment recommendation.</span>
      </section>

      <section className="kpi-grid">
        <article><span>Demo requests</span><strong>{requests.length}</strong></article>
        <article><span>Intelligence status</span><strong>Implemented</strong></article>
        <article><span>Current phase</span><strong>Full Workflow</strong></article>
      </section>

      <section id="requests" className="panel">
        <h2>Appointment Requests</h2>
        <p className="panel-hint">Click a request to select it, then run a review below.</p>
        {loading && <p>Loading requests…</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && requests.length === 0 && <p>No requests loaded. Run the seed script.</p>}
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
              <p>Flexibility: {item.flexibility_minutes} minutes</p>
              {item.emergency_flag_entered_by_staff && <p className="warning">Emergency workflow flag</p>}
            </article>
          ))}
        </div>
      </section>

      {selectedCode && (
        <section id="review" className="panel">
          <h2>Appointment Review — {selectedCode}</h2>
          <ReviewPanel key={selectedCode} requestCode={selectedCode} />
        </section>
      )}

      <section id="safety" className="panel">
        <h2>Operational Boundary</h2>
        <ul>
          <li>Six deterministic agents and the final operational decision are fully implemented (Posts #1.3–#1.5).</li>
          <li>No symptoms, diagnosis, treatment, medication, or clinical notes are stored or used.</li>
          <li>Emergency flags stop the workflow immediately and route staff outside COIP — no agent runs, nothing is scored.</li>
          <li>No LangGraph or LLM is included anywhere in this system.</li>
          <li>All doctor, slot, room, and queue values shown come from real backend data — nothing is fabricated on unknown or invalid requests.</li>
        </ul>
      </section>
    </>
  );
}
