import os
import pytest

from domain.core.analyzer import GraphAnalyzer
from domain.supporting.ledger import StructuralLedger
from domain.core.models import Skill, RelationalEdge


@pytest.fixture
def ledger(tmp_path):
    db = str(tmp_path / "analyzer_test.db")
    return StructuralLedger(db)


@pytest.fixture
def analyzer(ledger):
    return GraphAnalyzer(ledger)


def _seed_chain(ledger, count=5):
    """Create a chain of skills: s0 -> s1 -> s2 -> ... -> s(count-1)."""
    ids = [ledger.add_skill(f"skill_{i}", f"desc_{i}") for i in range(count)]
    for i in range(len(ids) - 1):
        ledger.add_edge(ids[i], ids[i + 1], "connected_to", weight=1.0)
    return ids


def _seed_star(ledger, spokes=5):
    """Create a hub node connected to N spoke nodes."""
    hub = ledger.add_skill("hub", "central node")
    spokes_ids = [ledger.add_skill(f"spoke_{i}", f"spoke desc {i}") for i in range(spokes)]
    for s in spokes_ids:
        ledger.add_edge(hub, s, "hub_link", weight=1.0)
    return hub, spokes_ids


class TestBuildGraph:
    def test_empty_graph(self, analyzer):
        analyzer.build_graph()
        assert len(analyzer.graph.nodes) == 0
        assert len(analyzer.graph.edges) == 0

    def test_graph_from_chain(self, analyzer, ledger):
        ids = _seed_chain(ledger, 4)
        analyzer.build_graph()
        assert len(analyzer.graph.nodes) == 4
        assert len(analyzer.graph.edges) == 3

    def test_rebuild_clears_previous(self, analyzer, ledger):
        _seed_chain(ledger, 3)
        analyzer.build_graph()
        assert len(analyzer.graph.nodes) == 3
        # Rebuild should not duplicate
        analyzer.build_graph()
        assert len(analyzer.graph.nodes) == 3


class TestCentralityMetrics:
    def test_empty_graph_returns_empty(self, analyzer):
        analyzer.build_graph()
        assert analyzer.get_centrality_metrics() == {}

    def test_metrics_contain_expected_keys(self, analyzer, ledger):
        _seed_chain(ledger, 3)
        analyzer.build_graph()
        metrics = analyzer.get_centrality_metrics()
        for node_metrics in metrics.values():
            assert "degree" in node_metrics
            assert "betweenness" in node_metrics
            assert "eigenvector" in node_metrics

    def test_hub_has_highest_degree(self, analyzer, ledger):
        hub, spokes = _seed_star(ledger, 5)
        analyzer.build_graph()
        metrics = analyzer.get_centrality_metrics()
        hub_degree = metrics[hub]["degree"]
        for s in spokes:
            assert hub_degree > metrics[s]["degree"]


class TestCommunityDetection:
    def test_empty_graph(self, analyzer):
        analyzer.build_graph()
        assert analyzer.detect_communities() == []

    def test_single_node(self, analyzer, ledger):
        ledger.add_skill("lonely", "no edges")
        analyzer.build_graph()
        # Single node -> not enough for communities
        assert analyzer.detect_communities() == []

    def test_connected_graph_has_communities(self, analyzer, ledger):
        _seed_chain(ledger, 5)
        analyzer.build_graph()
        communities = analyzer.detect_communities()
        # At least one community expected
        assert len(communities) >= 1
        # All nodes should be in some community
        all_nodes = set()
        for c in communities:
            all_nodes.update(c)
        assert all_nodes == set(analyzer.graph.nodes)


class TestBridgeNodes:
    def test_empty_graph(self, analyzer):
        analyzer.build_graph()
        assert analyzer.get_bridge_nodes() == []

    def test_chain_middle_is_bridge(self, analyzer, ledger):
        ids = _seed_chain(ledger, 5)
        analyzer.build_graph()
        bridges = analyzer.get_bridge_nodes(top_n=1)
        # Middle nodes of a chain have highest betweenness
        assert len(bridges) == 1
        assert bridges[0] in ids[1:-1]

    def test_top_n_limits(self, analyzer, ledger):
        _seed_chain(ledger, 10)
        analyzer.build_graph()
        assert len(analyzer.get_bridge_nodes(top_n=3)) == 3
