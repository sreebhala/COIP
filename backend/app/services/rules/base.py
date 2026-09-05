from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class DeterministicRule:
    rule_id: str
    name: str
    reason_code: str
    description: str

    def evaluate(self, facts: dict[str, Any]) -> tuple[bool, int, dict[str, Any]]:
        raise NotImplementedError("Implement COIP rules in Phase 1 Post #1.4")
