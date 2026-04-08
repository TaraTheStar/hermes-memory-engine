import pytest

from domain.core.anomaly_detector import ContextualAnomalyDetector
from domain.core.anomaly_config import MetricType, ThresholdProfile


@pytest.fixture
def detector():
    d = ContextualAnomalyDetector()
    profile = ThresholdProfile(
        name="test_profile",
        thresholds={
            MetricType.COMMUNITY_SIZE: 10.0,
            MetricType.EDGE_WEIGHT: 0.1,
            MetricType.GRAPH_DENSITY: 0.8,
        },
        sensitivity_multiplier=1.0,
    )
    d.register_profile("global", profile)
    return d


def test_no_anomaly_below_threshold(detector):
    result = detector.evaluate_metric(MetricType.COMMUNITY_SIZE, 5.0)
    assert result is None


def test_anomaly_above_threshold(detector):
    result = detector.evaluate_metric(MetricType.COMMUNITY_SIZE, 15.0)
    assert result is not None
    assert result.pattern_type == "COMMUNITY_SIZE"


def test_no_threshold_configured(detector):
    result = detector.evaluate_metric(MetricType.NODE_DEGREE, 100.0)
    assert result is None


def test_context_fallback_to_global(detector):
    result = detector.evaluate_metric(
        MetricType.COMMUNITY_SIZE, 15.0, context_id="unknown_context"
    )
    assert result is not None


def test_custom_context_profile(detector):
    strict_profile = ThresholdProfile(
        name="strict",
        thresholds={MetricType.COMMUNITY_SIZE: 3.0},
        sensitivity_multiplier=1.0,
    )
    detector.register_profile("strict_ctx", strict_profile)
    result = detector.evaluate_metric(
        MetricType.COMMUNITY_SIZE, 5.0, context_id="strict_ctx"
    )
    assert result is not None


def test_z_score_with_historical_values(detector):
    # Value of 100 with history around 10 should be anomalous
    historical = [10.0, 11.0, 9.0, 10.5, 10.2]
    result = detector.evaluate_metric(
        MetricType.COMMUNITY_SIZE, 100.0, historical_values=historical
    )
    assert result is not None
    assert "SIGMA_DEVIATION" in result.pattern_type


def test_z_score_normal_value(detector):
    # Value of 10.3 with history around 10 should NOT be anomalous
    historical = [10.0, 11.0, 9.0, 10.5, 10.2]
    result = detector.evaluate_metric(
        MetricType.COMMUNITY_SIZE, 10.3, historical_values=historical
    )
    assert result is None


def test_z_score_fallback_insufficient_history(detector):
    # With < 3 historical values, should fall back to simple threshold
    result = detector.evaluate_metric(
        MetricType.COMMUNITY_SIZE, 15.0, historical_values=[10.0, 11.0]
    )
    assert result is not None
    # Should be simple threshold result, not Z-score
    assert result.pattern_type == "COMMUNITY_SIZE"


def test_z_score_zero_stddev(detector):
    # All identical values => std_dev=0 => should return None
    result = detector.evaluate_complex_anomaly(
        MetricType.COMMUNITY_SIZE, 10.0, historical_values=[10.0, 10.0, 10.0]
    )
    assert result is None


def test_sensitivity_multiplier(detector):
    sensitive_profile = ThresholdProfile(
        name="sensitive",
        thresholds={MetricType.COMMUNITY_SIZE: 10.0},
        sensitivity_multiplier=0.5,  # Makes threshold effectively 5.0
    )
    detector.register_profile("sensitive_ctx", sensitive_profile)
    # 7.0 > 10.0 * 0.5 = 5.0, so should trigger
    result = detector.evaluate_metric(
        MetricType.COMMUNITY_SIZE, 7.0, context_id="sensitive_ctx"
    )
    assert result is not None
