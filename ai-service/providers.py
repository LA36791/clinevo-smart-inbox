from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from models import AnalysisResult


class AIProvider(ABC):
    @abstractmethod
    def analyze(self, text: str, **kwargs) -> Any:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass


class DeterministicProvider(AIProvider):
    """Rule-based deterministic provider with optional LLM/RAG enhancement."""

    def __init__(self):
        self._llm = None
        self._rag = None
        self._try_load_llm()

    def _try_load_llm(self):
        try:
            from llm_provider import LLMProvider
            llm = LLMProvider()
            if llm.is_available():
                self._llm = llm
        except Exception:
            pass
        try:
            from rag import HybridRAG
            self._rag = HybridRAG()
        except Exception:
            pass

    def is_available(self) -> bool:
        return True

    @property
    def using_llm(self) -> bool:
        return self._llm is not None

    @property
    def using_rag(self) -> bool:
        return self._rag is not None

    def analyze(self, text: str, **kwargs) -> Optional[AnalysisResult]:
        if self._llm:
            result = self._llm.analyze(text, **kwargs)
            if result:
                return result
        return None

    def retrieve_evidence(self, query: str, text: str = None,
                         pages: list = None, top_k: int = 3) -> str:
        if not self._rag:
            return text or ""
        if pages:
            self._rag.index_pages(pages)
        elif text:
            self._rag.index_text(text)
        return self._rag.get_evidence_context(query, top_k)
