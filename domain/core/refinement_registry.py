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

    _MAX_VALUE_LENGTH = 5000

    def apply(self, proposal: Any) -> None:
        """Applies an approved refinement proposal to the registry.

        Silently rejects proposals with invalid targets (non-string, empty,
        whitespace-only) or invalid values (non-string, oversized).
        """
        target = proposal.target_component
        value = proposal.proposed_state

        if not isinstance(target, str) or not target.strip():
            logger.warning("Rejecting refinement: invalid target %r", target)
            return
        if not isinstance(value, str):
            logger.warning("Rejecting refinement: proposed_state is not a string")
            return
        if len(value) > self._MAX_VALUE_LENGTH:
            logger.warning("Rejecting refinement: proposed_state exceeds %d chars", self._MAX_VALUE_LENGTH)
            return

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
