from typing import Any
from pydantic import BaseModel, Field

class AgentOutput(BaseModel):
    agent_name: str
    workflow_session_id: str
    appointment_request_id: str
    status: str = "completed"
    classification: str | None = None
    score: int | None = Field(default=None, ge=0, le=100)
    recommendation: str | None = None
    reasons: list[str] = Field(default_factory=list)
    rules_triggered: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    context_updated: list[str] = Field(default_factory=list)

class RuleResult(BaseModel):
    rule_id: str
    triggered: bool
    reason_code: str
    points: int = 0
    evidence: dict[str, Any] = Field(default_factory=dict)
