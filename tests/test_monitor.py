import uuid
import pytest
from datetime import datetime, timezone, timedelta

from domain.supporting.ledger import StructuralLedger
from domain.supporting.monitor import StateTracker, SnapshotAnomalyDetector
from domain.supporting.monitor_models import GraphSnapshot, AnomalyEvent
from domain.core.models import Skill, RelationalEdge


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "monitor_test.db")


@pytest.fixture
def ledger(db_path):
    return StructuralLedger(db_path)


def _add_skill(ledger, name):
    return ledger.add_skill(name, f"{name} description")


def _add_edge(ledger, source_id, target_id, weight=0.5):
    return ledger.add_edge(source_id, target_id, "related_to", weight)


# ── StateTracker ──


class TestStateTrackerEmptyGraph:
    def test_snapshot_on_empty_graph(self, ledger):
        tracker = StateTracker(ledger)
        snap = tracker.capture_snapshot()
        assert isinstance(snap, GraphSnapshot)
        assert snap.density == 0.0
        assert snap.community_count == 0
        assert snap.centrality_metrics == {}
        assert snap.metadata_tags["node_count"] == 0
        assert snap.metadata_tags["edge_count"] == 0

    def test_snapshot_has_uuid_and_timestamp(self, ledger):
        tracker = StateTracker(ledger)
        snap = tracker.capture_snapshot()
        assert snap.id is not None
        assert snap.timestamp is not None


class TestStateTrackerWithData:
    def test_density_with_triangle(self, ledger):
        """3 nodes, 3 edges = complete graph, density = 1.0."""
        s1 = _add_skill(ledger, "a")
        s2 = _add_skill(ledger, "b")
        s3 = _add_skill(ledger, "c")
        _add_edge(ledger, s1, s2)
        _add_edge(ledger, s2, s3)
        _add_edge(ledger, s1, s3)

        tracker = StateTracker(ledger)
        snap = tracker.capture_snapshot()
        assert abs(snap.density - 1.0) < 0.01
        assert snap.metadata_tags["node_count"] == 3
        assert snap.metadata_tags["edge_count"] == 3

    def test_density_with_chain(self, ledger):
        """3 nodes, 2 edges → density = 2*2 / (3*2) = 0.667."""
        s1 = _add_skill(ledger, "a")
        s2 = _add_skill(ledger, "b")
        s3 = _add_skill(ledger, "c")
        _add_edge(ledger, s1, s2)
        _add_edge(ledger, s2, s3)

        tracker = StateTracker(ledger)
        snap = tracker.capture_snapshot()
        assert abs(snap.density - 2 / 3) < 0.01

    def test_single_node_density_zero(self, ledger):
        _add_skill(ledger, "alone")
        tracker = StateTracker(ledger)
        snap = tracker.capture_snapshot()
        assert snap.density == 0.0

    def test_centrality_metrics_present(self, ledger):
        s1 = _add_skill(ledger, "a")
        s2 = _add_skill(ledger, "b")
        _add_edge(ledger, s1, s2)

        tracker = StateTracker(ledger)
        snap = tracker.capture_snapshot()
        assert len(snap.centrality_metrics) > 0
        for node_id, metrics in snap.centrality_metrics.items():
            assert "degree" in metrics
            assert "betweenness" in metrics

    def test_snapshot_persisted_to_db(self, ledger):
        tracker = StateTracker(ledger)
        snap = tracker.capture_snapshot()

        with ledger.session_scope() as session:
            row = session.get(GraphSnapshot, snap.id)
            assert row is not None
            assert row.density == snap.density


# ── SnapshotAnomalyDetector ──


def _insert_snapshot(ledger, timestamp, density=0.5, community_count=3, centrality_metrics=None):
    """Insert a snapshot and return an expunged copy safe for use outside the session."""
    snap = GraphSnapshot(
        id=str(uuid.uuid4()),
        timestamp=timestamp,
        density=density,
        community_count=community_count,
        centrality_metrics=centrality_metrics or {},
        metadata_tags={},
    )
    with ledger.session_scope() as session:
        session.add(snap)
        session.flush()
        session.expunge(snap)
    return snap


class TestSnapshotAnomalyDetector:
    def test_no_anomalies_with_insufficient_history(self, ledger):
        detector = SnapshotAnomalyDetector(ledger)
        now = datetime.now(timezone.utc)

        # Insert only 2 historical snapshots (need >= 3)
        for i in range(2):
            _insert_snapshot(ledger, now - timedelta(hours=2 - i))

        current = _insert_snapshot(ledger, now)
        anomalies = detector.detect_anomalies(current)
        assert anomalies == []

    def test_no_anomalies_on_stable_graph(self, ledger):
        detector = SnapshotAnomalyDetector(ledger)
        now = datetime.now(timezone.utc)

        for i in range(5):
            _insert_snapshot(ledger, now - timedelta(hours=5 - i), density=0.5, community_count=3)

        current = _insert_snapshot(ledger, now, density=0.5, community_count=3)
        anomalies = detector.detect_anomalies(current)
        assert len(anomalies) == 0

    def test_detects_density_divergence(self, ledger):
        detector = SnapshotAnomalyDetector(ledger, sensitivity=1.0)
        now = datetime.now(timezone.utc)

        for i in range(5):
            _insert_snapshot(ledger, now - timedelta(hours=5 - i), density=0.2, community_count=3)

        current = _insert_snapshot(ledger, now, density=0.9, community_count=3)
        anomalies = detector.detect_anomalies(current)
        density_anomalies = [a for a in anomalies if "density" in a.description.lower()]
        assert len(density_anomalies) >= 1

    def test_anomalies_persisted_to_db(self, ledger):
        detector = SnapshotAnomalyDetector(ledger, sensitivity=1.0)
        now = datetime.now(timezone.utc)

        for i in range(5):
            _insert_snapshot(ledger, now - timedelta(hours=5 - i), density=0.2, community_count=3)

        current = _insert_snapshot(ledger, now, density=0.9, community_count=3)
        anomalies = detector.detect_anomalies(current)
        assert len(anomalies) >= 1, "Expected at least one anomaly from density divergence"
        with ledger.session_scope() as session:
            count = session.query(AnomalyEvent).count()
            assert count >= len(anomalies)
