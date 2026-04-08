import os
import shutil
import pytest
from datetime import datetime, timezone

from domain.core.synthesis import SynthesisEngine
from domain.supporting.ledger import StructuralLedger


@pytest.fixture(scope="module")
def test_paths():
    db = "/tmp/hermes_test_synthesis.db"
    semantic = "/tmp/hermes_test_synthesis_semantic"

    if os.path.exists(db):
        os.remove(db)
    if os.path.exists(semantic):
        shutil.rmtree(semantic)
    os.makedirs(semantic)

    return db, semantic


@pytest.fixture
def engine(test_paths):
    db, semantic = test_paths
    return SynthesisEngine(semantic, db)


@pytest.fixture
def ledger(test_paths):
    db, _ = test_paths
    return StructuralLedger(db)


def test_temporal_scan_empty(engine):
    """Temporal scan on empty data should return 0 edges."""
    result = engine.run_temporal_correlation_scan()
    assert result == 0


def test_cooccurrence_scan_empty(engine):
    """Cooccurrence scan with no events should return 0."""
    result = engine.run_semantic_cooccurrence_scan()
    assert result == 0


def test_attribute_symmetry_scan_empty(engine):
    """Attribute scan with no skills should return 0."""
    result = engine.run_attribute_symmetry_scan()
    assert result == 0


def test_temporal_scan_skips_bad_timestamps(engine):
    """Events with missing or malformed timestamps should be skipped, not crash."""
    engine.semantic_memory.add_event(
        text="Event with no timestamp",
        metadata={"type": "test"},
    )
    engine.semantic_memory.add_event(
        text="Event with bad timestamp",
        metadata={"type": "test", "timestamp": "not-a-date"},
    )
    result = engine.run_temporal_correlation_scan()
    assert isinstance(result, int)


def test_temporal_scan_creates_edges(engine, ledger):
    """Events matching skill names within the time window should create edges."""
    skill_id = ledger.add_skill("Python", "Programming language")
    now = datetime.now(timezone.utc)
    engine.semantic_memory.add_event(
        text="I've been practicing python extensively today",
        metadata={"type": "learning", "timestamp": now.isoformat()},
    )
    result = engine.run_temporal_correlation_scan()
    assert result >= 1, "Expected at least one edge from skill-event correlation"


def test_incremental_scan(engine):
    """Second scan should not reprocess old events."""
    now = datetime.now(timezone.utc)
    engine.semantic_memory.add_event(
        text="First event for incremental test",
        metadata={"type": "test", "timestamp": now.isoformat()},
    )
    engine.run_temporal_correlation_scan()

    # Second scan with no new events
    result = engine.run_temporal_correlation_scan()
    assert result == 0


class TestSynthesisCooccurrence:
    @pytest.fixture(autouse=True)
    def _setup(self):
        db = "/tmp/hermes_test_synthesis_cooc.db"
        semantic = "/tmp/hermes_test_synthesis_cooc_semantic"

        if os.path.exists(db):
            os.remove(db)
        if os.path.exists(semantic):
            shutil.rmtree(semantic)
        os.makedirs(semantic)

        self.engine = SynthesisEngine(semantic, db)

    def test_cooccurrence_needs_two_events(self):
        """Cooccurrence scan needs at least 2 events."""
        now = datetime.now(timezone.utc)
        self.engine.semantic_memory.add_event(
            text="Solo event",
            metadata={"type": "test", "timestamp": now.isoformat()},
        )
        result = self.engine.run_semantic_cooccurrence_scan()
        assert result == 0
