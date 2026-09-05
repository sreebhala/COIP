export type AgentCardStatus = "pending" | "running" | "completed";

type Props = {
  agentName: string;
  responsibility: string;
  status: AgentCardStatus;
  inputUsed?: Record<string, unknown>;
  outputSummary?: Record<string, unknown>;
  reason?: string[];
  contextUpdated?: string[];
  auditStatus: string;
};

const STATUS_LABEL: Record<AgentCardStatus, string> = {
  pending: "Pending",
  running: "Running…",
  completed: "Completed",
};

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function AgentCard({
  agentName,
  responsibility,
  status,
  inputUsed,
  outputSummary,
  reason,
  contextUpdated,
  auditStatus,
}: Props) {
  return (
    <div className={`agent-card agent-card-${status}`}>
      <div className="agent-card-header">
        <span className={`agent-card-dot agent-card-dot-${status}`} />
        <div>
          <strong>{agentName}</strong>
          <p className="agent-card-responsibility">{responsibility}</p>
        </div>
        <span className={`agent-card-status agent-card-status-${status}`}>{STATUS_LABEL[status]}</span>
      </div>

      {status === "completed" && (
        <div className="agent-card-body">
          {outputSummary && (
            <div className="agent-card-row">
              <span>Output</span>
              <strong>
                {formatValue(outputSummary.classification)}
                {outputSummary.recommendation ? ` · ${formatValue(outputSummary.recommendation)}` : ""}
              </strong>
            </div>
          )}
          {reason && reason.length > 0 && (
            <div className="agent-card-row">
              <span>Reason</span>
              <strong>{reason.join(", ")}</strong>
            </div>
          )}
          {contextUpdated && contextUpdated.length > 0 && (
            <div className="agent-card-row">
              <span>Context updated</span>
              <strong>{contextUpdated.join(", ")}</strong>
            </div>
          )}
          {inputUsed && (
            <details className="agent-card-input">
              <summary>Input used</summary>
              <pre>{JSON.stringify(inputUsed, null, 2)}</pre>
            </details>
          )}
          <div className="agent-card-row">
            <span>Audit status</span>
            <strong>{auditStatus}</strong>
          </div>
        </div>
      )}
    </div>
  );
}
