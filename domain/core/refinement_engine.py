import logging
from typing import List, Dict, Any
import networkx as nx

logger = logging.getLogger(__name__)
from domain.supporting.ledger import StructuralLedger
from domain.core.analyzer import GraphAnalyzer
from domain.core.anomaly_detector import ContextualAnomalyDetector
from domain.core.anomaly_config import MetricType

class GraphRefinementProposal:
    def __init__(self, proposal_type: str, target_id: str, description: str, data: Dict[str, Any]):
        self.proposal_type = proposal_type  # 'PRUNE_EDGE', 'MERGE_COMMUNITY', 'CREATE_CONCEPT'
        self.target_id = target_id
        self.description = description
        self.data = data

class RefinementEngine:
    """
    Analyst component that identifies opportunities to simplify and optimize
    the knowledge graph hierarchy using context-aware anomaly detection.
    """
    def __init__(self,
                 structural_db_path_or_ledger,
                 detector: ContextualAnomalyDetector):
        if isinstance(structural_db_path_or_ledger, StructuralLedger):
            self.ledger = structural_db_path_or_ledger
        else:
            self.ledger = StructuralLedger(structural_db_path_or_ledger)
        self.analyzer = GraphAnalyzer(self.ledger)
        self.detector = detector

    
    def analyze_for_refinement(self, context_id: str = "global") -> List[GraphRefinementProposal]:
        """
        Scans the graph for structural bloat or redundancy using context-aware thresholds.
        Includes PREEMPTIVE detection based on trend velocity.
        """
        logger.info("Analyzing graph structure for context: %s...", context_id)
        self.analyzer.build_graph()
        graph = self.analyzer.graph
        proposals = []
        detected_events = []

        # 1. Detect Bloat: Overly large communities that need condensation
        communities = self.analyzer.detect_communities()
        for i, community in enumerate(communities):
            event = self.detector.evaluate_metric(
                MetricType.COMMUNITY_SIZE,
                float(len(community)),
                context_id=context_id
            )

            if event:
                detected_events.append(event)
                
                # Check if this is a PREEMPTIVE trend event
                is_preemptive = event.pattern_type == "COMMUNITY_SIZE_TREND_DIVERGENCE"
                desc_prefix = "PREEMPTIVE: Trend indicates imminent community explosion" if is_preemptive else "Anomaly detected in community size"
                
                proposal = GraphRefinementProposal(
                    proposal_type="MERGE_COMMUNITY",
                    target_id=f"community_{i}",
                    description=f"{desc_prefix} ({len(community)} nodes).",
                    data={"nodes": list(community), "event": event, "preemptive": is_preemptive}
                )
                proposals.append(proposal)

        # 2. Detect Redundancy: Low-weight edges
        for u, v, data in graph.edges(data=True):
            weight = data.get('weight', 1.0)
            event = self.detector.evaluate_metric(
                MetricType.EDGE_WEIGHT,
                weight,
                context_id=context_id
            )

            if event:
                detected_events.append(event)
                proposal = GraphRefinementProposal(
                    proposal_type="PRUNE_EDGE",
                    target_id=f"{u}->{v}",
                    description=f"Edge weight anomaly detected ({weight}). Potential redundancy.",
                    data={"source": u, "target": v, "event": event}
                )
                proposals.append(proposal)

        # 3. Detect Complexity Wall: High Global Density
        density = nx.density(graph)
        event = self.detector.evaluate_metric(
            MetricType.GRAPH_DENSITY,
            density,
            context_id=context_id
        )

        if event:
            detected_events.append(event)
            is_preemptive = event.pattern_type == "GRAPH_DENSITY_TREND_DIVERGENCE"
            desc_prefix = "PREEMPTIVE: Rapid density acceleration detected" if is_preemptive else "Global graph density anomaly"
            
            proposal = GraphRefinementProposal(
                proposal_type="GLOBAL_REBALANCE",
                target_id="graph_root",
                description=f"{desc_prefix} ({density:.4f}).",
                data={"density": density, "event": event, "preemptive": is_preemptive}
            )
            proposals.append(proposal)

        # Persist detected anomalies so InsightTrigger can find them.
        if detected_events:
            self._persist_anomaly_events(detected_events)

        return proposals


    def _persist_anomaly_events(self, events) -> None:
        """Write PatternDetectedEvents as AnomalyEvent rows.

        Uses a deduplication key based on pattern_type + context_id to prevent
        duplicate anomaly rows when ``analyze_for_refinement`` is called
        multiple times for the same graph state.
        """
        from domain.supporting.monitor_models import AnomalyEvent as AnomalyModel

        with self.ledger.session_scope() as session:
            for event in events:
                # Build a deterministic key so the same anomaly isn't persisted twice.
                ctx = event.metadata.get("context_id", "global")
                existing_rows = session.query(AnomalyModel).filter(
                    AnomalyModel.anomaly_type == event.pattern_type,
                    AnomalyModel.processed.is_(False),
                ).all()
                if any(
                    isinstance(row.trigger_data, dict) and row.trigger_data.get("context_id") == ctx
                    for row in existing_rows
                ):
                    continue
                session.add(ContextualAnomalyDetector.to_anomaly_event(event))
