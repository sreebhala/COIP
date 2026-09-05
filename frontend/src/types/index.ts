export type AppointmentRequest = {
  id: string;
  request_code: string;
  patient_id: string;
  location_id: string;
  requested_doctor_id?: string | null;
  appointment_type_id: string;
  preferred_date: string;
  preferred_time: string;
  flexibility_minutes: number;
  contact_channel?: string | null;
  confirmation_status: string;
  request_source: string;
  status: string;
  emergency_flag_entered_by_staff: boolean;
};

export type AppointmentRequestListResponse = {
  items: AppointmentRequest[];
  total: number;
};

export type AgentTraceEntry = {
  agent: string;
  classification: string;
  rules_triggered: string[];
};

export type ReviewResponse = {
  workflow_session_id: string;
  appointment_request_id: string;
  status: string;
  request_validation: { status: string };
  schedule: { category: string; doctor_code: string | null; date: string | null; time: string | null };
  queue: {
    category: string;
    projected_utilization_percent: number | null;
    estimated_wait_band_minutes: string | null;
  };
  resource: { room_code: string | null };
  attendance_follow_up: { confirmation_action: string | null; follow_up_status: string | null };
  decision: { category: string };
  reason_codes: string[];
  agent_trace: AgentTraceEntry[];
  explanation: string;
  audit_reference: string;
};

export type EmergencyStopResponse = {
  workflow_session_id: string;
  appointment_request_id: string;
  status: "emergency_stop";
  message: string;
};

export type ReviewResult = ReviewResponse | EmergencyStopResponse;

export type AuditRecord = {
  audit_reference: string;
  workflow_session_id: string;
  appointment_request_id: string;
  decision_type: string;
  decision: string;
  reason_codes: string[];
  evidence: Record<string, unknown>;
  explanation: string;
  created_at: string;
};

export type WorkflowTraceEntry = {
  sequence_number: number;
  agent_name: string;
  status: string;
  input_summary: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  rules_triggered: string[];
  context_updated: string[];
};

export type WorkflowTraceResponse = {
  workflow_session_id: string;
  agent_trace: WorkflowTraceEntry[];
};

export type WorkflowContextResponse = {
  workflow_session_id: string;
  appointment_request_id: string;
  routing_status: string;
  missing_data_flags: string[];
  appointment_request: Record<string, unknown>;
  patient_profile: Record<string, unknown>;
  clinic: Record<string, unknown>;
  location: Record<string, unknown>;
  appointment_type: Record<string, unknown>;
  requested_doctor: Record<string, unknown>;
  doctor_availability: unknown[];
  queue_snapshot: Record<string, unknown>;
  rooms: unknown[];
  attendance_summary: Record<string, unknown>;
  follow_up_summary: Record<string, unknown>;
  audit_reference: string | null;
  [key: string]: unknown;
};
