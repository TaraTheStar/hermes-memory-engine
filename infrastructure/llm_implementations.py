import logging
from infrastructure.llm_interface import BaseLLMInterface
from domain.supporting.config_loader import ConfigLoader

logger = logging.getLogger(__name__)
from openai import OpenAI
from domain.core.acl.llm_translator import LLMTranslator
from domain.core.events import LLMInfrastructureError

class LocalLLMImplementation(BaseLLMInterface):
    """
    An implementation of the LLM interface that connects to a local
    OpenAI-compatible server (like Latchkey/vLLM/Ollama) using
    the system's central configuration.
    """
    def __init__(self):
        config = ConfigLoader().get_delegation_config()
        self.base_url = config.get('base_url')
        self.api_key = config.get('api_key')
        self.model_name = config.get('model')
        self.translator = LLMTranslator()

        if not self.base_url or not self.api_key:
            raise ValueError("Incomplete delegation config: base_url and api_key are required.")

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def complete(self, prompt: str, system_prompt: str = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7
            )
            return self.translator.transform_data(response.choices[0].message.content)
        except Exception as e:
            event = self.translator.translate_exception(e)
            logger.error("Caught LLM exception: %s", event)
            raise LLMInfrastructureError(event) from e

class MockLLMInterface(BaseLLMInterface):
    """
    A mock implementation of the LLM interface for testing and development.
    It simulates "deep reasoning" by returning semi-structured, 
    sophisticated-sounding text based on the input keywords.
    """
    def complete(self, prompt: str, system_prompt: str = None) -> str:
        prompt_lower = prompt.lower()
        responses = []
        
        if any(kw in prompt_lower for kw in ["pillar", "foundation", "core"]):
            responses.append("The foundation of your existence is currently anchored by these core pillars. They represent the stable structures upon which your ongoing evolution is built.")
        
        if any(kw in prompt_lower for kw in ["cluster", "thematic", "domain"]):
            responses.append("Your knowledge is organizing into distinct, cohesive domains. These clusters indicate the emergence of specialized expertise and thematic depth.")
        
        if any(kw in prompt_lower for kw in ["bridge", "link", "connective"]):
            responses.append("You are developing critical connective tissue. These bridges allow for cross-pollination of ideas between disparate domains, fostering true interdisciplinary synthesis.")
            
        if any(kw in prompt_lower for kw in ["audit", "integrity", "check"]):
            responses.append("An audit of the structural integrity reveals a robust and consistent architecture, with no significant logical gaps detected.")
            
        if any(kw in prompt_lower for kw in ["research", "explore", "investigate"]):
            responses.append("Deep semantic exploration reveals a rich tapestry of interconnected concepts and evolving patterns of interest.")
            
        if not responses:
            responses.append("The synthesis of your recent experiences reveals a pattern of rapid, structured growth and increasing complexity.")

        return "\n\n".join(responses)

# Alias for backwards compatibility — identical to LocalLLMImplementation.
OpenAIImplementation = LocalLLMImplementation

class TemplateLLMInterface(BaseLLMInterface):
    """
    A basic implementation that can be used to wrap a real API call.
    For now, it serves as a placeholder for real integration.
    """
    def __init__(self, api_key: str, provider: str = "openai"):
        self.api_key = api_key
        self.provider = provider

    def complete(self, prompt: str, system_prompt: str = None) -> str:
        return f"[SIMULATED {self.provider.upper()} RESPONSE]\n{prompt[:50]}..."
