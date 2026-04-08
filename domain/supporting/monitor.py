import datetime
import logging
import uuid
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
    Compares the current snapshot against historical trends to predict and 
    detect significant structural shifts (The Sentinel).
    """
    def __init__(self, structural_db_path_or_ledger, sensitivity: float = 2.0):
        self.sensitivity = sensitivity
        
        if isinstance(structural_db_path_or_ledger, StructuralLedger):
            self.ledger = structural_db_path_or_ledger
        else:
            self.ledger = StructuralLedger(structural_db_path_or_ledger)

    @staticmethod
    def _normalize_ts(ts):
        """Ensure a datetime is timezone-aware (assume UTC if naive)."""
        from datetime import timezone
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts

    def _predict_trend(self, history: list, key: str, current_ts: any) -> dict:
        """Uses linear regression to predict the next value and its uncertainty."""
        import numpy as np

        if len(history) < 2:
            return {"expected": 0.0, "uncertainty": 0.0, "velocity": 0.0}

        # Convert timestamps to relative seconds for regression
        # Normalize to aware datetimes — SQLite drops tzinfo on round-trip
        start_ts = self._normalize_ts(history[0].timestamp)
        current_ts = self._normalize_ts(current_ts)
        x = np.array([(self._normalize_ts(h.timestamp) - start_ts).total_seconds() for h in history])
        
        # Extract values for the specific key
        y = []
        for h in history:
            val = getattr(h, key, 0.0) if hasattr(h, key) else 0.0
            y.append(val)
        
        y = np.array(y)
        
        # Linear regression: y = mx + c
        m, c = np.polyfit(x, y, 1)
        
        # Predict for current time
        current_x = (current_ts - start_ts).total_seconds()
        prediction = m * current_x + c
        
        # Uncertainty based on standard error of the estimate
        residuals = y - (m * x + c)
        uncertainty = np.std(residuals) if len(residuals) > 1 else 0.0
        
        return {"expected": max(0.0, prediction), "uncertainty": uncertainty, "velocity": m}

    def detect_anomalies(self, current_snapshot: any) -> list:
        import logging
        import uuid
        import numpy as np
        
        logger = logging.getLogger(__name__)
        logger.info("Sentinel scanning for structural anomalies...")
        anomalies = []

        with self.ledger.session_scope() as session:
            history = session.query(GraphSnapshot).filter(
                GraphSnapshot.timestamp < current_snapshot.timestamp
            ).order_by(GraphSnapshot.timestamp.desc()).all()
            # Reverse to get chronological order for regression
            history.reverse()

            if len(history) < 3:
                logger.info("Insufficient history for predictive analysis. Skipping.")
                return []

            # 1. MONITOR GLOBAL METRICS (Density & Community Count)
            for metric_name in ['density', 'community_count']:
                current_val = getattr(current_snapshot, metric_name)
                trend = self._predict_trend(history, metric_name, current_snapshot.timestamp)
                
                # Check for deviation from predicted trend
                deviation = abs(current_val - trend['expected'])
                threshold = trend['uncertainty'] * self.sensitivity
                
                # Add a baseline floor to avoid noise in very stable systems
                threshold = max(threshold, 0.05 if metric_name == 'density' else 0.5)

                if deviation > threshold:
                    anomalies.append(AnomalyEvent(
                        id=str(uuid.uuid4()),
                        anomaly_type="TREND_DIVERGENCE",
                        description=f"Metric '{metric_name}' diverged from predicted trend. (Actual: {current_val:.3f}, Predicted: {trend['expected']:.3f})",
                        severity="medium",
                        trigger_data={
                            "metric": metric_name,
                            "actual": current_val,
                            "expected": trend['expected'],
                            "velocity": trend['velocity']
                        }
                    ))

            # 2. MONITOR NODE HUB EMERGENCE (Velocity of Degree)
            for node_id, node_metrics in current_snapshot.centrality_metrics.items():
                current_degree = node_metrics.get('degree', 0.0)
                
                # Extract degree history for this specific node
                node_history_degrees = []
                node_history_ts = []
                for snap in history:
                    hist_metrics = snap.centrality_metrics.get(node_id, {})
                    if hist_metrics:
                        node_history_degrees.append(hist_metrics.get('degree', 0.0))
                        node_history_ts.append((self._normalize_ts(snap.timestamp) - self._normalize_ts(history[0].timestamp)).total_seconds())
                
                if len(node_history_degrees) >= 3:
                    x = np.array(node_history_ts)
                    y = np.array(node_history_degrees)
                    m, c = np.polyfit(x, y, 1)
                    
                    # Detect Acceleration: Is the degree increasing non-linearly?
                    # For simplicity here, we'll trigger if velocity is exceptionally high
                    if m > (self.sensitivity * 0.5): 
                        anomalies.append(AnomalyEvent(
                            id=str(uuid.uuid4()),
                            anomaly_type="STRUCTURAL_ACCELERATION",
                            description=f"Node '{node_id}' is showing rapid growth. (Degree Velocity: {m:.2f}/unit-time)",
                            severity="high",
                            trigger_data={"node_id": node_id, "velocity": m, "current_degree": current_degree}
                        ))

            if anomalies:
                for anomaly in anomalies:
                    session.add(anomaly)
                session.flush()
                for anomaly in anomalies:
                    session.expunge(anomaly)
                logger.info("Sentinel detected %d anomalies.", len(anomalies))
            else:
                logger.info("No structural divergences detected.")

            return anomalies
