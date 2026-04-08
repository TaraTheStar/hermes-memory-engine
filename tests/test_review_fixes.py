"""Tests verifying fixes for issues found during code review."""
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from domain.core.events import LLMInfrastructureError, InfrastructureErrorEvent
from domain.core.anomaly_detector import ContextualAnomalyDetector
from domain.core.anomaly_config import MetricType, ThresholdProfile


# --- #1: LLMInfrastructureError with proper InfrastructureErrorEvent ---

class TestLLMInfrastructureErrorConstruction:
    def test_empty_choices_raises_with_event_object(self):
        """The error raised on empty choices must carry an InfrastructureErrorEvent, not a string."""
        mock_response = MagicMock()
        mock_response.choices = []

        mock_openai = MagicMock()
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        loader = MagicMock()
        loader.get_delegation_config.return_value = {
            "base_url": "http://localhost:8080", "api_key": "test-key", "model": "test"
        }
        with patch("infrastructure.llm_implementations.ConfigLoader", return_value=loader):
            with patch("infrastructure.llm_implementations.OpenAI", mock_openai):
                from infrastructure.llm_implementations import LocalLLMImplementation
                impl = LocalLLMImplementation()

        with pytest.raises(LLMInfrastructureError) as exc_info:
            impl.complete("test prompt")

        # The event attribute must be an InfrastructureErrorEvent, not a string
        assert isinstance(exc_info.value.event, InfrastructureErrorEvent)
        # The original EMPTY_CHOICES error is re-wrapped by the outer except,
        # so verify the original message is preserved in the chain
        assert "EMPTY_CHOICES" in str(exc_info.value)


# --- #2: Sensitivity multiplier direction ---

class TestSensitivityMultiplierDirection:
    def _make_detector(self, multiplier: float):
        d = ContextualAnomalyDetector()
        profile = ThresholdProfile(
            name="test",
            thresholds={MetricType.COMMUNITY_SIZE: 10.0},
            z_score_thresholds={MetricType.COMMUNITY_SIZE: 3.0},
            sensitivity_multiplier=multiplier,
        )
        d.register_profile("global", profile)
        return d

    def test_higher_multiplier_is_more_sensitive_simple(self):
        """sensitivity_multiplier=2.0 should lower the effective threshold (10/2=5), triggering on 7."""
        d = self._make_detector(2.0)
        result = d.evaluate_metric(MetricType.COMMUNITY_SIZE, 7.0)
        assert result is not None, "Higher sensitivity should trigger on value below raw threshold"

    def test_lower_multiplier_is_less_sensitive_simple(self):
        """sensitivity_multiplier=0.5 should raise the effective threshold (10/0.5=20), not triggering on 15."""
        d = self._make_detector(0.5)
        result = d.evaluate_metric(MetricType.COMMUNITY_SIZE, 15.0)
        assert result is None, "Lower sensitivity should NOT trigger on value that normally would"

    def test_higher_multiplier_is_more_sensitive_zscore(self):
        """sensitivity_multiplier=2.0 should halve the z-score threshold, detecting smaller deviations."""
        d = self._make_detector(2.0)
        # With history around 10, std_dev ~0.7. Value 12: z_score ~2.8
        # With multiplier 2.0: effective threshold = 3.0/2.0 = 1.5, so 2.8 > 1.5 => anomaly
        historical = [10.0, 10.5, 9.5, 10.2, 9.8]
        result = d.evaluate_metric(MetricType.COMMUNITY_SIZE, 12.0, historical_values=historical)
        assert result is not None, "Higher sensitivity should detect smaller z-score deviations"

    def test_default_multiplier_no_change(self):
        """sensitivity_multiplier=1.0 should not alter thresholds."""
        d = self._make_detector(1.0)
        # 5.0 < 10.0 threshold => no anomaly
        result = d.evaluate_metric(MetricType.COMMUNITY_SIZE, 5.0)
        assert result is None


# --- #4: Anomaly deduplication checking all rows ---

class TestAnomalyDeduplication:
    def test_dedup_finds_matching_context_in_later_rows(self):
        """Deduplication should check ALL matching rows, not just the first."""
        from domain.core.refinement_engine import RefinementEngine
        from domain.core.events import PatternDetectedEvent, EventSeverity
        from domain.supporting.monitor_models import AnomalyEvent as AnomalyModel

        db_path = os.path.join(tempfile.mkdtemp(), "dedup_test.db")
        from domain.supporting.ledger import StructuralLedger
        ledger = StructuralLedger(db_path)
        detector = ContextualAnomalyDetector()
        engine = RefinementEngine(ledger, detector)

        # Pre-populate DB with two unprocessed anomalies of the same type but different contexts
        with ledger.session_scope() as session:
            session.add(AnomalyModel(
                id="existing-1", anomaly_type="COMMUNITY_SIZE",
                description="test", severity="medium",
                trigger_data={"context_id": "ctx_A"}
            ))
            session.add(AnomalyModel(
                id="existing-2", anomaly_type="COMMUNITY_SIZE",
                description="test", severity="medium",
                trigger_data={"context_id": "ctx_B"}
            ))

        # Try to persist an event with context_id=ctx_B — should be deduplicated
        event = PatternDetectedEvent(
            severity=EventSeverity.WARNING,
            source="test",
            pattern_type="COMMUNITY_SIZE",
            metadata={"context_id": "ctx_B"}
        )
        engine._persist_anomaly_events([event])

        with ledger.session_scope() as session:
            count = session.query(AnomalyModel).filter(
                AnomalyModel.anomaly_type == "COMMUNITY_SIZE"
            ).count()
            # Should still be 2, not 3 — the duplicate was caught
            assert count == 2, f"Expected 2 rows (dedup should have prevented insert), got {count}"


# --- #7: Event retry cap in monitoring loop ---

class TestEventRetryCap:
    def test_event_failure_counts_initialized(self):
        """AutonomousOrchestrator should have event failure tracking."""
        from application.autonomous_orchestrator import AutonomousOrchestrator
        orch = AutonomousOrchestrator(registry={})
        assert hasattr(orch, '_event_failure_counts')
        assert hasattr(orch, '_max_event_retries')
        assert orch._max_event_retries == 3


# --- #10: Type casting of trigger_data values ---

class TestTriggerDataTypeCasting:
    def test_community_shift_casts_counts_to_int(self):
        """String values in trigger_data should be cast to int, not interpolated raw."""
        from domain.core.insight_trigger import InsightTrigger
        db_path = os.path.join(tempfile.mkdtemp(), "cast_test.db")
        from domain.supporting.ledger import StructuralLedger
        trigger = InsightTrigger(StructuralLedger(db_path), goal_runner=None)

        snap = {
            "id": "t1",
            "anomaly_type": "COMMUNITY_SHIFT",
            "description": "test",
            "trigger_data": {"old_count": "INJECT_PAYLOAD", "new_count": "5"},
        }
        # Should raise ValueError from int() on the injected string
        with pytest.raises(ValueError):
            trigger._generate_goal_from_snapshot(snap)

    def test_hub_emergence_casts_degree_to_float(self):
        """String values for new_degree should be cast to float."""
        from domain.core.insight_trigger import InsightTrigger
        db_path = os.path.join(tempfile.mkdtemp(), "cast_test2.db")
        from domain.supporting.ledger import StructuralLedger
        trigger = InsightTrigger(StructuralLedger(db_path), goal_runner=None)

        snap = {
            "id": "t2",
            "anomaly_type": "HUB_EMERGENCE",
            "description": "test",
            "trigger_data": {"node_id": "node_1", "new_degree": "INJECT"},
        }
        with pytest.raises(ValueError):
            trigger._generate_goal_from_snapshot(snap)
