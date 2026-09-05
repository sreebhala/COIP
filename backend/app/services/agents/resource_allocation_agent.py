"""
Resource Allocation Agent — COIP-RES-001 to COIP-RES-005.

Boundary: does not infer clinical equipment needs — only matches the
appointment type's pre-configured required_room_type.

Phase 1 documented limitation: the current context does not carry
per-room appointment/overlap data (Post #1.3's context only tracks
existing_appointments at the doctor level, not per-room), so COIP-RES-002
("lowest overlapping load") is approximated by picking the first
configured room, and COIP-RES-004 ("required room unavailable at this
specific time") cannot be distinguished from "no rooms configured" with
current context data. This is called out explicitly here rather than
fabricating room-level occupancy data that Post #1.3 does not provide.
"""
from typing import Any

from app.schemas.common import AgentOutput
from app.services.agents.base import DeterministicAgent
from app.services.rules import catalogue as rules

AGENT_NAME = "ResourceAllocationAgent"


class ResourceAllocationAgent(DeterministicAgent):
    name = AGENT_NAME

    def run(self, context: dict[str, Any]) -> AgentOutput:
        appointment_type = context.get("appointment_type", {})
        rooms = context.get("rooms", [])
        required_room_type = appointment_type.get("required_room_type")

        rules_triggered: list[str] = []
        reason_codes: list[str] = []
        evidence: dict[str, Any] = {"required_room_type": required_room_type}
        recommendation = None

        if not required_room_type:
            category = "Not Required"
            rules_triggered.append(rules.RES_003_ROOM_NOT_REQUIRED.rule_id)
            reason_codes.append(rules.RES_003_ROOM_NOT_REQUIRED.reason_code)
        elif not rooms:
            category = "Needs Review"
            rules_triggered.append(rules.RES_005_ROOM_CONFIG_MISSING.rule_id)
            reason_codes.append(rules.RES_005_ROOM_CONFIG_MISSING.reason_code)
        else:
            category = "Room Recommended"
            recommendation = rooms[0]["room_code"]
            rules_triggered.append(rules.RES_001_REQUIRED_ROOM_AVAILABLE.rule_id)
            reason_codes.append(rules.RES_001_REQUIRED_ROOM_AVAILABLE.reason_code)
            if len(rooms) > 1:
                rules_triggered.append(rules.RES_002_LOWEST_LOAD_ROOM.rule_id)
                reason_codes.append(rules.RES_002_LOWEST_LOAD_ROOM.reason_code)
            evidence["candidate_rooms"] = rooms

        return AgentOutput(
            agent_name=self.name,
            workflow_session_id=context.get("workflow_session_id", ""),
            appointment_request_id=context.get("appointment_request_id", ""),
            classification=category,
            recommendation=recommendation,
            reasons=reason_codes,
            rules_triggered=rules_triggered,
            evidence=evidence,
            context_updated=["resource_result"],
        )
