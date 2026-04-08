import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)
from domain.supporting.monitor_models import AnomalyEvent
from domain.core.ports import GoalRunner
from domain.supporting.ledger import StructuralLedger


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
        Each anomaly is committed independently so a failure on one does not
        roll back progress on previously processed anomalies.
        """
        context = context or {}
        with self.ledger.session_scope() as session:
            unprocessed = session.query(AnomalyEvent).filter(
                AnomalyEvent.processed == False
            ).order_by(AnomalyEvent.timestamp.desc()).limit(5).all()
            anomaly_ids = [a.id for a in unprocessed]

        if not anomaly_ids:
            logger.info("No unprocessed anomalies to handle.")
            return

        logger.info("Found %d unprocessed anomalies. Generating investigation goals...", len(anomaly_ids))

        for anomaly_id in anomaly_ids:
            with self.ledger.session_scope() as session:
                anomaly = session.get(AnomalyEvent, anomaly_id)
                if anomaly is None or anomaly.processed:
                    continue

                goal = self._generate_goal_from_anomaly(anomaly)
                if goal:
                    logger.info("Triggering goal runner with goal: '%s'", goal)
                    try:
                        await self.goal_runner.run_goal(goal, context)
                    except Exception:
                        logger.exception("Goal runner failed for anomaly %s", anomaly_id)
                        continue
                    anomaly.processed = True
                else:
                    logger.warning("Could not generate goal for anomaly: %s", anomaly.anomaly_type)

    def _generate_goal_from_anomaly(self, anomaly: AnomalyEvent) -> str:
        """
        Translates a structural event into a sophisticated natural language goal.
        """
        a_type = anomaly.anomaly_type
        data = anomaly.trigger_data or {}

        if a_type == "HUB_EMERGENCE":
            node_id = data.get("node_id", "Unknown Node")
            new_deg = data.get("new_degree", 0.0)
            return (f"Investigate the sudden emergence of '{node_id}' as a significant hub. "
                    f"It has reached a degree centrality of {new_deg:.2f}. "
                    "Analyze its role in bridging disparate knowledge domains and its potential impact on overall connectivity.")

        elif a_type == "COMMUNITY_SHIFT":
            old_c = data.get("old_count", 0)
            new_c = data.get("new_count", 0)
            return (f"Analyze the significant shift in community structure. "
                    f"The knowledge cluster count changed from ~{old_c} to {new_c}. "
                    "Identify if this represents a merger of existing domains or a fragmentation of a major cluster.")

        elif a_type == "DENSITY_SHIFT":
            return "Analyze the sudden change in graph density. Investigate if this indicates a rapid burst of knowledge ingestion or a potential structural instability."

        # Fallback generic goal
        return f"Perform a deep structural audit in response to a detected {a_type} event: {anomaly.description}"
