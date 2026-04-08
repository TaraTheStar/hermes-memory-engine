from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class RefinementRegistry:
    """
    A registry of approved refinements (prompts, tool configs, etc.)
    that agents can query to evolve their behavior dynamically.

    When constructed with a ``StructuralLedger``, refinements are persisted
    to the database and survive process restarts.  Without a ledger the
    registry operates in-memory only (useful for tests).
    """

    _MAX_VALUE_LENGTH = 5000

    def __init__(self, ledger=None):
        self._ledger = ledger
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
        if not isinstance(value, str):
            logger.warning("Rejecting refinement: proposed_state is not a string")
            return
        if len(value) > self._MAX_VALUE_LENGTH:
            logger.warning("Rejecting refinement: proposed_state exceeds %d chars", self._MAX_VALUE_LENGTH)
            return

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
