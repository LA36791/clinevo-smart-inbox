from abc import ABC, abstractmethod
from typing import Dict, Any

class AIProvider(ABC):
    @abstractmethod
    def analyze(self, text: str) -> Dict[str, Any]:
        pass

class DeterministicProvider(AIProvider):
    def analyze(self, text: str) -> Dict[str, Any]:
        return {"text": text}
