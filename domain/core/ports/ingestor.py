from abc import ABC, abstractmethod
from typing import Dict, Any, Protocol
from domain.core.agent import AgentResult

class IntelligenceIngestor(Protocol):
    """
    The protocol for components that transform agentic findings 
    into durable, structured memory events.
    """
    async def ingest(self, result: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Takes the orchestration result and processes it into memory.
        Returns True if ingestion was successful, False otherwise.
        """
        ...
