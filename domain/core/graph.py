import networkx as nx
import os
from typing import List, Dict, Any, Optional

class RelationshipGraph:
    def __init__(self, graph_path: str = "/data/hermes_memory_engine/structural/graph.gml"):
        self.graph_path = os.path.expanduser(graph_path)
        self.G = nx.Graph()

    def add_node(self, node_id: str, node_type: str, properties: Dict[str, Any]):
        """
        Adds a node to the graph representing a structured or semantic entity.
        """
        self.G.add_node(node_id, type=node_type, **properties)

    def add_edge(self, source_id: str, target_id: str, relationship_type: str, weight: float = 1.0):
        """
        Adds a relationship edge between two nodes.
        """
        self.G.add_edge(source_id, target_id, relation=relationship_type, weight=weight)

    def save(self):
        """Persists the graph to disk."""
        nx.write_gml(self.G, self.graph_path)

    def load(self):
        """Loads the graph from disk."""
        if os.path.exists(self.graph_path):
            self.G = nx.read_gml(self.graph_path)

    def get_connected_entities(self, node_id: str) -> List[Dict[str, Any]]:
        """Finds all entities directly connected to a given node."""
        if not self.G.has_node(node_id):
            return []
        
        neighbors = self.G.neighbors(node_id)
        results = []
        for n in neighbors:
            data = self.G.nodes[n]
            rel = self.G[node_id][n].get('relation', 'connected_to')
            results.append({
                "id": n,
                "type": data.get('type'),
                "relation": rel,
                "properties": {k: v for k, v in data.items() if k != 'type'}
            })
        return results

    def find_clusters(self) -> List[set]:
        """Finds strongly connected components (clusters of ideas)."""
        return list(nx.connected_components(self.G))

if __name__ == "__main__":
    # Quick Test
    rg = RelationshipGraph()
    print("Testing RelationshipGraph...")
    
    rg.add_node("ms_1", "milestone", {"title": "First PR"})
    rg.add_node("sk_1", "skill", {"name": "Python"})
    rg.add_edge("ms_1", "sk_1", "requires")
    
    print(f"Nodes: {rg.G.nodes(data=True)}")
    print(f"Edges: {rg.G.edges(data=True)}")
    
    rg.save()
    print("Graph saved.")
