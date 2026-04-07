from abc import ABC, abstractmethod

class BaseLLMInterface(ABC):
    """
    An abstract interface for interacting with Large Language Models.
    Allows the InsightSynthesizer to be decoupled from specific providers.
    """

    @abstractmethod
    def complete(self, prompt: str, system_prompt: str = None) -> str:
        """
        Sends a prompt to the LLM and returns the generated text.

        Args:
            prompt: The user/task prompt.
            system_prompt: An optional system instruction to set the persona/context.

        Returns:
            The LLM's response as a string.
        """
        pass
