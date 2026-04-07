import networkx as nx
from typing import Dict, List, Any, Set
from domain.supporting.ledger import StructuralLedger
from domain.core.models import RelationalEdge, Skill, Milestone, Project

class GraphAnalyzer:
    def __init__(self, structural_db_path: str):
        self.ledger = StructuralLedger(structural_db_path)
        self.graph = nx.Graph()

    def build_graph(self):
        """
        Constructs a NetworkX graph from the Structural Ledger.
        Nodes represent entities (Skill, Milestone, Project), 
        and edges represent RelationalEdges.
        """
        with self.ledger.session_scope() as session:
            edges = session.query(RelationalEdge).all()

            for edge in edges:
                self.graph.add_edge(
                    edge.source_id,
                    edge.target_id,
                    type=edge.relationship_type,
                    weight=edge.weight
                )

    def get_centrality_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Calculates various centrality metrics to find 'power nodes'.
        """
        if len(self.graph.nodes) == 0:
            return {}

        # Degree: The raw number of connections a node has.
        degree = dict(self.graph.degree())
        
        # Betweenness Centrality: How often a node acts as a bridge.
        betweenness = nx.betweenness_centrality(self.graph)
        
        # Eigenvector Centrality: Connection to other well-connected nodes.
        try:
            eigenvector = nx.eigenvector_centrality(self.graph, max_iter=1000)
        except nx.PowerIterationFailedConvergence:
            eigenvector = {}

        metrics = {}
        for node in self.graph.nodes:
            metrics[node] = {
                "degree": float(degree.get(node, 0.0)),
                "betweenness": betweenness.get(node, 0.0),
                "eigenvector": eigenvector.get(node, 0.0)
            }
        return metrics

    def detect_communities(self) -> List[Set[str]]:
        """
        Detects clusters of highly connected nodes using the Louvain method.
        """
        if len(self.graph.nodes) < 2:
            return []
            
        # Using greedy modularity communities as a robust default for small graphs
        communities = nx.community.greedy_modularity_communities(self.graph)
        return [set(c) for c in communities]

    def get_bridge_nodes(self, top_n: int = 5) -> List[str]:
        """
        Identifies nodes with high betweenness centrality.
        """
        betweenness = nx.betweenness_centrality(self.graph)
        sorted_nodes = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)
        return [node for node, score in sorted_nodes[:top_n]]

