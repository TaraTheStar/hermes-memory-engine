import uuid
import datetime
from typing import List, Dict, Any, Optional, Set
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models import Base
from core.monitor_models import AnomalyEvent
from core.orchestrator import Orchestrator

class InsightTrigger:
    """
    The bridge between detected anomalies and the Agentic Orchestrator.
    Translates mathematical events into actionable investigation goals.
    """
    def __init__(self, structural_db_path: str, orchestrator: Orchestrator):
        self.engine = create_engine(f"sqlite:///{structural_db_path}")
        self.Session = sessionmaker(bind=self.engine)
        self.orchestrator = orchestrator

    async def process_new_anomalies(self):
        """
        Fetches unhandled anomalies and triggers orchestration for each.
        """
        session = self.Session()
        try:
            # In a real production system, we would track 'processed' status.
            # For this prototype, we will pull recent anomalies.
            recent_anomalies = session.query(AnomalyEvent).order_by(AnomalyEvent.timestamp.desc()).limit(5).all()
            
            if not recent_anomalies:
                print("[InsightTrigger] No recent anomalies to process.")
                return

            print(f"[InsightTrigger] Found {len(recent_anomalies)} recent anomalies. Generating investigation goals...")

            for anomaly in recent_anomalies:
                goal = self._generate_goal_from_anomaly(anomaly)
                if goal:
                    print(f"[InsightTrigger] -> Triggering Orchestrator with goal: '{goal}'")
                    # Trigger the orchestrator asynchronously
                    await self.orchestrator.run_goal(goal)
                else:
                    print(f"[InsightTrigger] Could not generate goal for anomaly: {anomaly.anomaly_type}")

        except Exception as e:
            print(f"[InsightTrigger] Error processing anomalies: {e}")
        finally:
            session.close()

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
