from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class RefinementRegistry:
    """
    A persistent registry of approved refinements (prompts, tool configs, etc.)
    that agents can query to evolve their behavior dynamically.
    """
    def __init__(self):
        self._refinements: Dict[str, Any] = {}

    def apply(self, proposal: Any) -> None:
        """Applies an approved refinement proposal to the registry."""
        target = proposal.target_component
        value = proposal.proposed_state
        
        logger.info("Applying refinement to '%s': %s", target, value)
        self._refinements[target] = value

    def get_refinement(self, target: str) -> Optional[Any]:
        """Retrieves a refinement for a specific target component."""
        return self._refinements.get(target)

    def get_all(self) -> Dict[str, Any]:
        """Returns all currently active refinements."""
        return self._refinements.copy()

# Singleton instance for easy access within the session
registry = RefinementRegistry()
