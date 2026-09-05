import type {
  AppointmentRequestListResponse,
  AuditRecord,
  ReviewResult,
  WorkflowContextResponse,
  WorkflowTraceResponse,
} from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function postRequest<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>("/health"),
  appointmentRequests: () => request<AppointmentRequestListResponse>("/api/v1/appointment-requests"),

  // Post #1.6 additions — real backend data only, no mocked responses.
  reviewAppointment: (appointment_request_id: string) =>
    postRequest<ReviewResult>("/api/v1/reviews/appointment", {
      appointment_request_id,
      review_reason: "appointment_review",
    }),
  getWorkflowTrace: (workflowSessionId: string) =>
    request<WorkflowTraceResponse>(`/api/v1/workflows/${workflowSessionId}/trace`),
  getWorkflowContext: (workflowSessionId: string) =>
    request<WorkflowContextResponse>(`/api/v1/workflows/${workflowSessionId}/context`),
  getAuditRecord: (auditReference: string) =>
    request<AuditRecord>(`/api/v1/audit/${auditReference}`),
};
