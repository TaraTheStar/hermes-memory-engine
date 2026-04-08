import datetime
import logging
import uuid
import statistics
from typing import Dict, List, Any, Optional, Set

logger = logging.getLogger(__name__)
from domain.core.analyzer import GraphAnalyzer
from domain.supporting.monitor_models import GraphSnapshot, AnomalyEvent
from domain.supporting.ledger import StructuralLedger


class StateTracker:
    """
    Responsible for periodic snapshotting of the graph's structural state.
    """
    def __init__(self, structural_db_path_or_ledger):
        if isinstance(structural_db_path_or_ledger, StructuralLedger):
            self.ledger = structural_db_path_or_ledger
        else:
            self.ledger = StructuralLedger(structural_db_path_or_ledger)
        self.analyzer = GraphAnalyzer(self.ledger)

    def capture_snapshot(self) -> GraphSnapshot:
        logger.info("Capturing graph snapshot...")
        self.analyzer.build_graph()

        metrics = self.analyzer.get_centrality_metrics()
        communities = self.analyzer.detect_communities()

        nodes_count = len(self.analyzer.graph.nodes)
        edges_count = len(self.analyzer.graph.edges)
        density = 0.0
        if nodes_count > 1:
            density = (2 * edges_count) / (nodes_count * (nodes_count - 1))

        snapshot = GraphSnapshot(
            id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            density=density,
            community_count=len(communities),
            centrality_metrics=metrics,
            metadata_tags={"node_count": nodes_count, "edge_count": edges_count}
        )

        with self.ledger.session_scope() as session:
            session.add(snapshot)
            logger.info("Snapshot saved: %s (Nodes: %d, Communities: %d)", snapshot.id, nodes_count, len(communities))
            # Expunge so the object is usable after the session closes.
            session.flush()
            session.expunge(snapshot)

        return snapshot


class SnapshotAnomalyDetector:
    """
    Compares the current snapshot against historical data to find significant patterns.
    """
    def __init__(self, structural_db_path_or_ledger, sensitivity: float = 2.0):
        if isinstance(structural_db_path_or_ledger, StructuralLedger):
            self.ledger = structural_db_path_or_ledger
        else:
            self.ledger = StructuralLedger(structural_db_path_or_ledger)
        self.sensitivity = sensitivity

    def detect_anomalies(self, current_snapshot: GraphSnapshot) -> List[AnomalyEvent]:
        logger.info("Scanning for structural anomalies...")
        anomalies = []

        with self.ledger.session_scope() as session:
            history = session.query(GraphSnapshot).filter(
                GraphSnapshot.timestamp < current_snapshot.timestamp
            ).order_by(GraphSnapshot.timestamp.desc()).all()

            if len(history) < 2:
                logger.info("Insufficient history for statistical analysis. Skipping.")
                return []

            for node_id, node_metrics in current_snapshot.centrality_metrics.items():
                current_degree = node_metrics.get('degree', 0.0)

                historical_degrees = []
                for snap in history:
                    hist_metrics = snap.centrality_metrics.get(node_id, {})
                    if hist_metrics:
                        historical_degrees.append(hist_metrics.get('degree', 0.0))

                if not historical_degrees and current_degree > 5.0:
                    anomalies.append(AnomalyEvent(
                        id=str(uuid.uuid4()),
                        anomaly_type="HUB_EMERGENCE",
                        description=f"New node '{node_id}' has emerged as an immediate hub with degree {current_degree:.2f}.",
                        severity="high",
                        trigger_data={"node_id": node_id, "new_degree": current_degree, "is_new": True}
                    ))
                    continue

                if len(historical_degrees) >= 2:
                    mean_deg = statistics.mean(historical_degrees)
                    stdev_deg = statistics.stdev(historical_degrees) if len(historical_degrees) > 1 else 0.0

                    threshold = max(mean_deg + (self.sensitivity * stdev_deg), mean_deg + 0.3)

                    if current_degree > threshold:
                        anomalies.append(AnomalyEvent(
                            id=str(uuid.uuid4()),
                            anomaly_type="HUB_EMERGENCE",
                            description=f"Node '{node_id}' has emerged as a significant hub. (Degree: {current_degree:.2f}, Hist Mean: {mean_deg:.2f})",
                            severity="medium",
                            trigger_data={"node_id": node_id, "new_degree": current_degree, "mean_degree": mean_deg}
                        ))

            historical_counts = [s.community_count for s in history]
            mean_comm = sum(historical_counts) / len(historical_counts)

            if abs(current_snapshot.community_count - mean_comm) >= 1:
                anomalies.append(AnomalyEvent(
                    id=str(uuid.uuid4()),
                    anomaly_type="COMMUNITY_SHIFT",
                    description=f"Significant shift in community structure: Count changed from ~{mean_comm:.1f} to {current_snapshot.community_count}.",
                    severity="medium",
                    trigger_data={"old_count": mean_comm, "new_count": current_snapshot.community_count}
                ))

            if anomalies:
                for anomaly in anomalies:
                    session.add(anomaly)
                logger.info("Detected %d anomalies.", len(anomalies))
            else:
                logger.info("No significant anomalies detected.")

            return anomalies
