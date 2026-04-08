"""Task #23: Test preemptive detection paths in refinement_engine.py
(COMMUNITY_SIZE_TREND_DIVERGENCE and GRAPH_DENSITY_TREND_DIVERGENCE)."""
import pytest
from domain.core.refinement_engine import RefinementEngine
from domain.core.anomaly_detector import ContextualAnomalyDetector
from domain.core.anomaly_config import MetricType, ThresholdProfile
from domain.supporting.ledger import StructuralLedger


@pytest.fixture
def ledger(tmp_path):
    return StructuralLedger(str(tmp_path / "refine.db"))


@pytest.fixture
def detector():
    d = ContextualAnomalyDetector()
    # Register a profile with low thresholds and historical data requirements
    profile = ThresholdProfile(
        name="test_preemptive",
        thresholds={
            MetricType.COMMUNITY_SIZE: 50.0,  # High threshold so simple won't trigger
            MetricType.GRAPH_DENSITY: 5.0,
            MetricType.EDGE_WEIGHT: 0.1,
        },
        z_score_thresholds={
            MetricType.COMMUNITY_SIZE: 2.0,
            MetricType.GRAPH_DENSITY: 2.0,
        },
        sensitivity_multiplier=1.0,
        min_sample_size=3,
    )
    d.register_profile("global", profile)
    return d


class TestPreemptiveDetection:
    def test_community_size_trend_divergence(self, ledger, detector):
        """When historical data is available, trend divergence should produce PREEMPTIVE proposals."""
        # Seed nodes to create a large community
        for i in range(8):
            ledger.add_skill(f"skill_{i}", f"desc_{i}")
        # Connect them all to form a community
        with ledger.session_scope() as session:
            from domain.core.models import Skill
            skills = session.query(Skill).all()
            for i in range(len(skills)):
                for j in range(i + 1, len(skills)):
                    ledger.add_edge(skills[i].id, skills[j].id, "collaboration", 0.8, session=session)

        # Override evaluate_metric to simulate trend divergence
        original_eval = detector.evaluate_metric

        def fake_eval(metric_type, value, context_id="global", historical_values=None):
            if metric_type == MetricType.COMMUNITY_SIZE and value >= 8:
                from domain.core.events import PatternDetectedEvent, EventSeverity
                return PatternDetectedEvent(
                    severity=EventSeverity.WARNING,
                    source="ContextualAnomalyDetector",
                    pattern_type="COMMUNITY_SIZE_TREND_DIVERGENCE",
                    metadata={"context_id": context_id, "value": value},
                )
            return original_eval(metric_type, value, context_id, historical_values)

        detector.evaluate_metric = fake_eval
        engine = RefinementEngine(ledger, detector)
        proposals = engine.analyze_for_refinement()

        preemptive_proposals = [p for p in proposals if p.data.get("preemptive")]
        assert len(preemptive_proposals) >= 1
        assert "PREEMPTIVE" in preemptive_proposals[0].description

    def test_density_trend_divergence(self, ledger, detector):
        """GRAPH_DENSITY_TREND_DIVERGENCE should produce preemptive GLOBAL_REBALANCE."""
        # Seed a small dense graph
        for i in range(3):
            ledger.add_skill(f"dense_sk_{i}", f"desc_{i}")
        with ledger.session_scope() as session:
            from domain.core.models import Skill
            skills = session.query(Skill).all()
            for i in range(len(skills)):
                for j in range(i + 1, len(skills)):
                    ledger.add_edge(skills[i].id, skills[j].id, "dense_link", 0.9, session=session)

        original_eval = detector.evaluate_metric

        def fake_eval(metric_type, value, context_id="global", historical_values=None):
            if metric_type == MetricType.GRAPH_DENSITY:
                from domain.core.events import PatternDetectedEvent, EventSeverity
                return PatternDetectedEvent(
                    severity=EventSeverity.WARNING,
                    source="ContextualAnomalyDetector",
                    pattern_type="GRAPH_DENSITY_TREND_DIVERGENCE",
                    metadata={"context_id": context_id, "density": value},
                )
            return original_eval(metric_type, value, context_id, historical_values)

        detector.evaluate_metric = fake_eval
        engine = RefinementEngine(ledger, detector)
        proposals = engine.analyze_for_refinement()

        rebalance = [p for p in proposals if p.proposal_type == "GLOBAL_REBALANCE"]
        assert len(rebalance) >= 1
        assert rebalance[0].data.get("preemptive") is True
        assert "PREEMPTIVE" in rebalance[0].description
