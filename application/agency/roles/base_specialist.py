import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseSpecialist(ABC):
    """
    The base class for all agency specialists.
    Each specialist has a unique persona (system prompt) and a specific capability.
    """
    def __init__(self, name: str, system_prompt: str, llm_implementation: Any):
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm_implementation

    @abstractmethod
    async def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        The core execution logic for the specialist.
        Returns the result of the task.
        """
        pass

    async def _call_llm(self, prompt: str) -> str:
        """Helper to call the LLM with the specialist's persona."""
        if not self.llm:
            raise RuntimeError(f"LLM not initialized for specialist: {self.name}")
        return await asyncio.to_thread(self.llm.complete, prompt, self.system_prompt)
