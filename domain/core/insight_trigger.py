import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
from domain.supporting.monitor_models import AnomalyEvent
from domain.core.ports import GoalRunner
from domain.supporting.ledger import StructuralLedger
from domain.core.prompt_sanitizer import sanitize_field


class InsightTrigger:
    """
    The bridge between detected anomalies and the Agentic Orchestrator.
    Translates mathematical events into actionable investigation goals.
    """
    def __init__(self, structural_db_path_or_ledger, goal_runner: GoalRunner):
        if isinstance(structural_db_path_or_ledger, StructuralLedger):
            self.ledger = structural_db_path_or_ledger
        else:
            self.ledger = StructuralLedger(structural_db_path_or_ledger)
        self.goal_runner = goal_runner

    async def process_new_anomalies(self, context: Optional[Dict[str, Any]] = None):
        """
        Fetches unhandled anomalies and triggers orchestration for each.
        Each anomaly is claimed (marked processed) within its own session
        before the goal runner is invoked, preventing duplicate processing
        when concurrent callers race on the same anomaly.
        """
        context = context or {}

        # Collect anomaly IDs and immediately mark them as processed in a
        # single session to prevent TOCTOU races between concurrent callers.
        anomaly_snapshots = []
        with self.ledger.session_scope() as session:
            unprocessed = session.query(AnomalyEvent).filter(
                AnomalyEvent.processed.is_(False)
            ).order_by(AnomalyEvent.timestamp.desc()).limit(5).all()

            if not unprocessed:
                logger.info("No unprocessed anomalies to handle.")
                return

            for anomaly in unprocessed:
                anomaly.processed = True
                anomaly_snapshots.append({
                    "id": anomaly.id,
                    "anomaly_type": anomaly.anomaly_type,
                    "description": anomaly.description,
                    "trigger_data": dict(anomaly.trigger_data) if anomaly.trigger_data else {},
                })
            # Session commits here, atomically claiming all anomalies.

        logger.info("Found %d unprocessed anomalies. Generating investigation goals...", len(anomaly_snapshots))

        for snap in anomaly_snapshots:
            goal = self._generate_goal_from_snapshot(snap)
            if goal:
                logger.info("Triggering goal runner with goal: '%s'", goal)
                try:
                    await self.goal_runner.run_goal(goal, context)
                except Exception:
                    logger.exception("Goal runner failed for anomaly %s", snap["id"])
            else:
                logger.warning("Could not generate goal for anomaly: %s — skipping.",
                               snap["anomaly_type"])

    def _generate_goal_from_snapshot(self, snap: Dict[str, Any]) -> str:
        """
        Translates a structural event into a sophisticated natural language goal.
        User-controlled fields are wrapped via ``sanitize_field`` to prevent
        prompt boundary spoofing.
        """
        a_type = snap["anomaly_type"]
        data = snap.get("trigger_data") or {}

        if a_type == "HUB_EMERGENCE":
            node_id = sanitize_field(data.get("node_id", "Unknown Node"), "node_id")
            new_deg = float(data.get("new_degree", 0.0))
            return (f"Investigate the sudden emergence of {node_id} as a significant hub. "
                    f"It has reached a degree centrality of {new_deg:.2f}. "
                    "Analyze its role in bridging disparate knowledge domains and its potential impact on overall connectivity.")

        elif a_type == "COMMUNITY_SHIFT":
            old_c = int(data.get("old_count", 0))
            new_c = int(data.get("new_count", 0))
            return (f"Analyze the significant shift in community structure. "
                    f"The knowledge cluster count changed from ~{old_c} to {new_c}. "
                    "Identify if this represents a merger of existing domains or a fragmentation of a major cluster.")

        elif a_type == "DENSITY_SHIFT":
            return "Analyze the sudden change in graph density. Investigate if this indicates a rapid burst of knowledge ingestion or a potential structural instability."

        # Fallback generic goal
        safe_type = sanitize_field(a_type, "anomaly_type")
        safe_desc = sanitize_field(snap.get("description", ""), "description")
        return f"Perform a deep structural audit in response to a detected {safe_type} event: {safe_desc}"
