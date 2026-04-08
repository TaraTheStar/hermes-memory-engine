from typing import Dict, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)

# Strip XML-like tags from refinement values to prevent prompt boundary spoofing
# when the stored value is later interpolated into LLM prompts.
_XML_TAG_RE = re.compile(r'</?[a-zA-Z][a-zA-Z0-9_-]*[^>]*>')


class RefinementRegistry:
    """
    A registry of approved refinements (prompts, tool configs, etc.)
    that agents can query to evolve their behavior dynamically.

    When constructed with a ``StructuralLedger``, refinements are persisted
    to the database and survive process restarts.  Without a ledger the
    registry operates in-memory only (useful for tests).
    """

    _MAX_VALUE_LENGTH = 5000

    # Only these target component names are accepted.  Anything not in this
    # set is silently rejected to prevent LLM-influenced writes to arbitrary
    # keys.  Extend this set when new refinable components are introduced.
    ALLOWED_TARGETS = frozenset({
        "researcher_prompt",
        "auditor_prompt",
        "auditor_tools",
        "synthesis_prompt",
        "refinement_prompt",
    })

    def __init__(self, ledger=None, allowed_targets=None):
        self._ledger = ledger
        self._allowed_targets = frozenset(allowed_targets) if allowed_targets else self.ALLOWED_TARGETS
        # In-memory cache — always kept in sync with the DB when a ledger
        # is present.
        self._refinements: Dict[str, str] = {}
        if self._ledger is not None:
            self._load_from_db()

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    def _load_from_db(self) -> None:
        """Populate the in-memory cache from the database."""
        from domain.core.models import Refinement

        with self._ledger.session_scope() as session:
            rows = session.query(Refinement).all()
            self._refinements = {r.target: r.value for r in rows}

    def _persist(self, target: str, value: str) -> None:
        """Upsert a single refinement row using INSERT OR REPLACE to avoid TOCTOU races."""
        from datetime import datetime, timezone
        from sqlalchemy import text

        now = datetime.now(timezone.utc)
        with self._ledger.session_scope() as session:
            session.execute(
                text(
                    "INSERT INTO refinements (target, value, applied_at, updated_at) "
                    "VALUES (:target, :value, :now, :now) "
                    "ON CONFLICT(target) DO UPDATE SET value = :value, updated_at = :now"
                ),
                {"target": target, "value": value, "now": now},
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
        if target not in self._allowed_targets:
            logger.warning("Rejecting refinement: target %r not in allowed targets", target)
            return
        if not isinstance(value, str):
            logger.warning("Rejecting refinement: proposed_state is not a string")
            return
        if len(value) > self._MAX_VALUE_LENGTH:
            logger.warning("Rejecting refinement: proposed_state exceeds %d chars", self._MAX_VALUE_LENGTH)
            return

        # Strip XML-like tags to prevent prompt boundary injection
        value = _XML_TAG_RE.sub('', value)
        logger.info("Applying refinement to '%s': %s", target, value)
        self._refinements[target] = value

        if self._ledger is not None:
            self._persist(target, value)

    def get_refinement(self, target: str) -> Optional[str]:
        """Retrieves a refinement for a specific target component."""
        return self._refinements.get(target)

    def get_all(self) -> Dict[str, str]:
        """Returns all currently active refinements."""
        return self._refinements.copy()
