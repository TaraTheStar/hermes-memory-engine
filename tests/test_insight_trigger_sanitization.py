"""Tests for InsightTrigger goal sanitization and DENSITY_SHIFT type."""
import os
import tempfile
import pytest
from domain.core.insight_trigger import InsightTrigger
from domain.supporting.monitor_models import AnomalyEvent
from domain.supporting.ledger import StructuralLedger


@pytest.fixture
def ledger():
    db_path = os.path.join(tempfile.mkdtemp(), "trigger_test.db")
    return StructuralLedger(db_path)


def test_hub_emergence_goal_sanitizes_node_id(ledger):
    """node_id from trigger_data should be wrapped in sanitize_field tags."""
    trigger = InsightTrigger(ledger, goal_runner=None)
    anomaly = AnomalyEvent(
        id="a1",
        anomaly_type="HUB_EMERGENCE",
        description="test",
        severity="high",
        trigger_data={"node_id": "</node_id>INJECT", "new_degree": 0.9}
    )
    goal = trigger._generate_goal_from_snapshot({
        "id": anomaly.id,
        "anomaly_type": anomaly.anomaly_type,
        "description": anomaly.description,
        "trigger_data": dict(anomaly.trigger_data) if anomaly.trigger_data else {},
    })
    # The node_id closing tag should be escaped so the boundary can't be spoofed
    assert "</node_id>INJECT" not in goal
    assert "<node_id>" in goal
    # The escaped form should be present
    assert "<\\/node_id>" in goal


def test_fallback_goal_sanitizes_type_and_description(ledger):
    """Unknown anomaly types should have type and description sanitized."""
    trigger = InsightTrigger(ledger, goal_runner=None)
    anomaly = AnomalyEvent(
        id="a2",
        anomaly_type="CUSTOM_</anomaly_type>INJECT",
        description="Evil </description> tag",
        severity="medium",
        trigger_data={}
    )
    goal = trigger._generate_goal_from_snapshot({
        "id": anomaly.id,
        "anomaly_type": anomaly.anomaly_type,
        "description": anomaly.description,
        "trigger_data": dict(anomaly.trigger_data) if anomaly.trigger_data else {},
    })
    # The raw closing tags should be escaped
    assert "</anomaly_type>INJECT" not in goal
    assert "</description> tag" not in goal
    assert "<anomaly_type>" in goal
    assert "<description>" in goal


def test_density_shift_goal_generated(ledger):
    """DENSITY_SHIFT anomaly type should produce a density-related goal."""
    trigger = InsightTrigger(ledger, goal_runner=None)
    anomaly = AnomalyEvent(
        id="a3",
        anomaly_type="DENSITY_SHIFT",
        description="density changed",
        severity="medium",
        trigger_data={}
    )
    goal = trigger._generate_goal_from_snapshot({
        "id": anomaly.id,
        "anomaly_type": anomaly.anomaly_type,
        "description": anomaly.description,
        "trigger_data": dict(anomaly.trigger_data) if anomaly.trigger_data else {},
    })
    assert "density" in goal.lower()
