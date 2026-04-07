from typing import List, Dict, Any, Set, Optional
import networkx as nx
from core.ledger import StructuralLedger
from core.analyzer import GraphAnalyzer

class RefinementProposal:
    def __init__(self, proposal_type: str, target_id: str, description: str, data: Dict[str, Any]):
        self.proposal_type = proposal_type  # 'PRUNE_EDGE', 'MERGE_COMMUNITY', 'CREATE_CONCEPT'
        self.target_id = target_id
        self.description = description
        self.data = data

class RefinementEngine:
    """
    Analyst component that identifies opportunities to simplify and optimize
    the knowledge graph hierarchy.
    """
    def __init__(self, structural_db_path: str, density_threshold: float = 0.1, community_size_threshold: int = 20):
        self.ledger = StructuralLedger(structural_db_path)
        self.analyzer = GraphAnalyzer(structural_db_path)
        self.density_threshold = density_threshold
        self.community_size_threshold = community_size_threshold

    def analyze_for_refinement(self) -> List[RefinementProposal]:
        """
        Scans the graph for structural bloat or redundancy.
        """
        print("[RefinementEngine] Analyzing graph structure for optimization opportunities...")
        self.analyzer.build_graph()
        graph = self.analyzer.graph
        proposals = []

        # 1. Detect Bloat: Overly large communities that need condensation
        communities = self.analyzer.detect_communities()
        for i, community in enumerate(communities):
            if len(community) > self.community_size_threshold:
                # Propose a 'Merge' or 'Condensation' into a concept node
                proposal = RefinementProposal(
                    proposal_type="MERGE_COMMUNITY",
                    target_id=f"community_{i}",
                    description=f"Community {i} has grown to {len(community)} nodes. Proposing condensation into a Concept Node.",
                    data={"nodes": list(community), "current_size": len(community)}
                )
                proposals.append(proposal)

        # 2. Detect Redundancy: Low-weight edges in high-density areas
        # (Simplified heuristic: edges with weight < threshold in highly connected clusters)
        for u, v, data in graph.edges(data=True):
            if data.get('weight', 1.0) < 0.1:
                proposal = RefinementProposal(
                    proposal_type="PRUNE_EDGE",
                    target_id=f"{u}->{v}",
                    description=f"Low-weight edge between {u} and {v} detected. Potential redundancy.",
                    data={"source": u, "target": v, "weight": data.get('weight')}
                )
                proposals.append(proposal)

        # 3. Detect Complexity Wall: High Global Density
        density = nx.density(graph)
        if density > self.density_threshold:
            proposal = RefinementProposal(
                proposal_type="GLOBAL_REBALANCE",
                target_id="graph_root",
                description=f"Global graph density ({density:.4f}) exceeds threshold ({self.density_threshold}). Proposing structural rebalancing.",
                data={"density": density}
            )
            proposals.append(proposal)

        return proposals
