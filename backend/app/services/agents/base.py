from abc import ABC, abstractmethod
from typing import Any
from app.schemas.common import AgentOutput

class DeterministicAgent(ABC):
    name: str

    @abstractmethod
    def run(self, context: dict[str, Any]) -> AgentOutput:
        raise NotImplementedError
