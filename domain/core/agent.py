import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from infrastructure.llm_interface import BaseLLMInterface

class AgentStatus:
    IDLE = "idle"
    THINKING = "thinking"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"

class HermesAgent(ABC):
    """
    The abstract base class for all specialized agents within the Hermes ecosystem.
    """
    def __init__(self, agent_id: str, role: str, llm: BaseLLMInterface):
        self.agent_id = agent_id
        self.role = role
        self.llm = llm
        self.status = AgentStatus.IDLE
        self.history: List[Dict[str, Any]] = []

    @abstractmethod
    async def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        The primary execution loop of the agent.
        
        Args:
            task: A dictionary containing 'goal' and 'constraints'.
            context: A dictionary containing the 'memory_slice' and 'relevant_entities'.
            
        Returns:
            A dictionary containing 'finding', 'confidence', and 'evidence'.
        """
        pass

    def _log(self, message: str, level: str = "INFO"):
        self.history.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "level": level,
            "message": message
        })

    def _build_system_prompt(self) -> str:
        return f"You are a specialized {self.role} agent within the Hermes Memory Engine. Your purpose is to execute specific tasks with high precision and return structured findings."
