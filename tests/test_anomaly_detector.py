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
        z_score_thresholds={
            MetricType.COMMUNITY_SIZE: 3.0,
            MetricType.EDGE_WEIGHT: 3.0,
            MetricType.GRAPH_DENSITY: 3.0,
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
        sensitivity_multiplier=2.0,  # Makes threshold effectively 5.0
    )
    detector.register_profile("sensitive_ctx", sensitive_profile)
    # 7.0 > 10.0 / 2.0 = 5.0, so should trigger
    result = detector.evaluate_metric(
        MetricType.COMMUNITY_SIZE, 7.0, context_id="sensitive_ctx"
    )
    assert result is not None


def test_trend_divergence_detection(detector):
    """Value that doesn't breach z-score but diverges from trend should trigger TREND_DIVERGENCE."""
    # Steady upward trend: 10, 12, 14, 16, 18 (slope ~2/step)
    # Predicted next value ~20. If we provide 30, it's within z-score range
    # (std_dev is ~3.16, z_score of 30 vs mean=14 would be ~5, still SIGMA)
    # Use a tighter trend: values with low variance but clear trend
    historical = [10.0, 10.1, 10.2, 10.3, 10.4]
    # Predicted next value ~10.5. Value 11.5 diverges from trend but
    # z-score = |11.5 - 10.2| / 0.158 ~ 8.2 — too high, will hit SIGMA first.
    #
    # To hit TREND_DIVERGENCE only, we need z_score <= threshold but trend deviation > threshold.
    # Use values with higher variance so z-score doesn't fire:
    historical = [8.0, 12.0, 9.0, 11.0, 10.0]  # mean=10, std_dev~1.58
    # z_threshold is 3.0, so value needs z < 3 => within [10 - 4.74, 10 + 4.74] = [5.26, 14.74]
    # Trend: polyfit on [0,1,2,3,4] -> slope ~0.2, intercept ~9.6
    # prediction at x=5: 0.2*5 + 9.6 = 10.6
    # trend_threshold = mean * 0.1 = 1.0
    # So a value of 13.0: z_score = |13 - 10| / 1.58 ~ 1.9 (below 3.0)
    # trend_deviation = |13 - 10.6| = 2.4 > 1.0 — should trigger TREND_DIVERGENCE
    result = detector.evaluate_complex_anomaly(
        MetricType.COMMUNITY_SIZE, 13.0, historical_values=historical
    )
    assert result is not None
    assert "TREND_DIVERGENCE" in result.pattern_type
    assert result.metadata["velocity"] is not None
    assert result.metadata["prediction"] is not None


def test_trend_divergence_not_triggered_when_on_trend(detector):
    """Value close to the predicted trend should not trigger any anomaly."""
    historical = [8.0, 12.0, 9.0, 11.0, 10.0]
    # prediction at x=5 ~10.6, trend_threshold ~1.0
    # value 10.5 is well within both z-score and trend bounds
    result = detector.evaluate_complex_anomaly(
        MetricType.COMMUNITY_SIZE, 10.5, historical_values=historical
    )
    assert result is None


def test_to_anomaly_event():
    """to_anomaly_event should produce a well-formed AnomalyEvent."""
    from domain.core.events import PatternDetectedEvent, EventSeverity
    event = PatternDetectedEvent(
        severity=EventSeverity.WARNING,
        source="TestDetector",
        pattern_type="HUB_EMERGENCE",
        metadata={"context_id": "test", "value": 5.0}
    )
    anomaly = ContextualAnomalyDetector.to_anomaly_event(event)
    assert anomaly.anomaly_type == "HUB_EMERGENCE"
    assert anomaly.severity == "medium"
    assert "TestDetector" in anomaly.description
    assert anomaly.trigger_data["context_id"] == "test"
    assert anomaly.id  # Should have a UUID


def test_edge_weight_below_threshold_triggers(detector):
    """EDGE_WEIGHT uses below-threshold logic: low weight = anomaly."""
    result = detector.evaluate_metric(MetricType.EDGE_WEIGHT, 0.01)
    assert result is not None
    assert result.pattern_type == "EDGE_WEIGHT"


def test_edge_weight_above_threshold_no_anomaly(detector):
    """EDGE_WEIGHT above threshold should NOT trigger (it's a below-threshold metric)."""
    result = detector.evaluate_metric(MetricType.EDGE_WEIGHT, 5.0)
    assert result is None
