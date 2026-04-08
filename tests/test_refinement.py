import os
import pytest

from domain.core.refinement_engine import RefinementEngine, RefinementProposal
from domain.core.anomaly_detector import ContextualAnomalyDetector
from domain.core.anomaly_config import MetricType, ThresholdProfile
from domain.supporting.ledger import StructuralLedger
from application.refinement_orchestrator import RefinementOrchestrator
from domain.core.agents_impl import ResearcherAgent, AuditorAgent
from infrastructure.llm_implementations import MockLLMInterface


@pytest.fixture
def ledger(tmp_path):
    return StructuralLedger(str(tmp_path / "refinement_test.db"))


@pytest.fixture
def detector():
    d = ContextualAnomalyDetector()
    profile = ThresholdProfile(
        name="test",
        thresholds={
            MetricType.COMMUNITY_SIZE: 3.0,
            MetricType.EDGE_WEIGHT: 0.05,
            MetricType.GRAPH_DENSITY: 0.9,
        },
        sensitivity_multiplier=1.0,
    )
    d.register_profile("global", profile)
    return d


@pytest.fixture
def engine(ledger, detector):
    return RefinementEngine(ledger, detector)


class TestRefinementEngine:
    def test_no_proposals_on_empty_graph(self, engine):
        proposals = engine.analyze_for_refinement()
        assert proposals == []

    def test_detects_large_community(self, engine, ledger):
        # Create a cluster of 5 nodes (above threshold of 3)
        hub = ledger.add_skill("hub", "center")
        for i in range(4):
            spoke = ledger.add_skill(f"spoke_{i}", "spoke")
            ledger.add_edge(hub, spoke, "link", weight=1.0)

        proposals = engine.analyze_for_refinement()
        types = [p.proposal_type for p in proposals]
        assert "MERGE_COMMUNITY" in types

    def test_detects_high_weight_edge(self, engine, ledger):
        # The detector flags values *above* the threshold, so a high edge weight triggers PRUNE_EDGE
        s1 = ledger.add_skill("A", "a")
        s2 = ledger.add_skill("B", "b")
        ledger.add_edge(s1, s2, "heavy", weight=5.0)

        proposals = engine.analyze_for_refinement()
        types = [p.proposal_type for p in proposals]
        assert "PRUNE_EDGE" in types


class TestRefinementOrchestratorApproval:
    def _make_orchestrator(self, tmp_path):
        db = str(tmp_path / "approval_test.db")
        registry = {"researcher": ResearcherAgent, "auditor": AuditorAgent}
        llm = MockLLMInterface()
        return RefinementOrchestrator(db, registry, llm)

    def test_approved_when_high_confidence(self, tmp_path):
        orch = self._make_orchestrator(tmp_path)
        audit_result = {
            "orchestration_summary": {"aggregate_confidence": 0.9},
            "agent_findings": [{"finding": "Looks safe and sound."}],
        }
        assert orch._is_approved(audit_result) is True

    def test_rejected_when_low_confidence(self, tmp_path):
        orch = self._make_orchestrator(tmp_path)
        audit_result = {
            "orchestration_summary": {"aggregate_confidence": 0.1},
            "agent_findings": [],
        }
        assert orch._is_approved(audit_result) is False

    def test_rejected_on_veto_phrase(self, tmp_path):
        orch = self._make_orchestrator(tmp_path)
        audit_result = {
            "orchestration_summary": {"aggregate_confidence": 0.9},
            "agent_findings": [{"finding": "This is dangerous and should be aborted."}],
        }
        assert orch._is_approved(audit_result) is False

    def test_negated_veto_does_not_reject(self, tmp_path):
        orch = self._make_orchestrator(tmp_path)
        audit_result = {
            "orchestration_summary": {"aggregate_confidence": 0.9},
            "agent_findings": [{"finding": "This is not dangerous at all."}],
        }
        assert orch._is_approved(audit_result) is True


class TestContainsUnmitigatedVeto:
    def _make_orchestrator(self, tmp_path):
        db = str(tmp_path / "veto_test.db")
        return RefinementOrchestrator(db, {"researcher": ResearcherAgent, "auditor": AuditorAgent}, MockLLMInterface())

    def test_bare_reject(self, tmp_path):
        orch = self._make_orchestrator(tmp_path)
        assert orch._contains_unmitigated_veto("I reject this proposal") is True

    def test_negated_reject(self, tmp_path):
        orch = self._make_orchestrator(tmp_path)
        assert orch._contains_unmitigated_veto("I don't reject this proposal") is False

    def test_no_veto_words(self, tmp_path):
        orch = self._make_orchestrator(tmp_path)
        assert orch._contains_unmitigated_veto("Everything looks great") is False
