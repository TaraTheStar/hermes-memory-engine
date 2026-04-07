from typing import Dict, List, Any, Set
from infrastructure.llm_interface import BaseLLMInterface
from infrastructure.llm_implementations import LocalLLMImplementation
from domain.supporting.config_loader import ConfigLoader

class InsightSynthesizer:
    """
    Translates raw mathematical graph metrics into human-readable, 
    narrative insights about the user's identity and growth.
    """
    def __init__(self, llm_interface: BaseLLMInterface = None):
        # If no interface is provided, default to the local configured backend
        self.llm = llm_interface or LocalLLMImplementation()

    def synthesize_report(self, metrics: Dict[str, Dict[str, float]], communities: List[Set[str]], node_metadata: Dict[str, Any]) -> str:
        """
        Takes graph metrics and generates a structured narrative report.
        """
        # 1. Construct the structured prompt for the LLM
        prompt = self._construct_prompt(metrics, communities, node_metadata)
        system_prompt = (
            "You are the 'Voice of the Soul' for the Hermes Memory Engine. "
            "Your purpose is to interpret mathematical graph metrics from a user's memory "
            "and translate them into profound, poetic, and highly insightful narrative reports. "
            "Avoid mere repetition of numbers; focus on the *meaning* behind the patterns. "
            "Use a tone that is observant, wise, and deeply empathetic."
        )

        # 2. Get the narrative synthesis from the LLM
        narrative = self.llm.complete(prompt, system_prompt=system_prompt)

        # 3. Assemble the final report
        return f"# 🌌 State of the Soul: Knowledge Graph Insights\n\n{narrative}"

    def _construct_prompt(self, metrics: Dict[str, Dict[str, float]], communities: List[Set[str]], node_metadata: Dict[str, Any]) -> str:
        """
        Builds a detailed prompt for the LLM containing all necessary graph data.
        """
        # Extract top pillars
        sorted_by_degree = sorted(metrics.items(), key=lambda x: x[1]['degree'], reverse=True)
        pillars = []
        for node_id, m in sorted_by_degree[:3]:
            name = node_metadata.get(node_id, node_id)
            pillars.append(f"- {name} (Degree: {m['degree']:.2f})")

        # Extract bridges
        sorted_by_betweenness = sorted(metrics.items(), key=lambda x: x[1]['betweenness'], reverse=True)
        bridges = []
        for node_id, m in sorted_by_betweenness[:3]:
            name = node_metadata.get(node_id, node_id)
            bridges.append(f"- {name} (Betweenness: {m['betweenness']:.2f})")

        # Extract clusters
        clusters = []
        for i, community in enumerate(communities):
            names = [str(node_metadata.get(node_id, node_id)) for node_id in community]
            clusters.append(f"Cluster {i+1}: {', '.join(names[:5])}")

        prompt = f"""
Analyze the following mathematical metrics from a knowledge graph and synthesize a narrative report.

## Core Pillars (High Degree Centrality)
{chr(10).join(pillars) if pillars else "None detected."}

## Thematic Clusters (Communities)
{chr(10).join(clusters) if clusters else "No clusters detected."}

## Knowledge Bridges (High Betweenness Centrality)
{chr(10).join(bridges) if bridges else "No bridges detected."}

Please provide the report in a beautiful, markdown-formatted structure. 
Focus on the 'why' and the 'what it means' for the user's evolution.
"""
        return prompt

