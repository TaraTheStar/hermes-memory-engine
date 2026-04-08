"""Tests for synthesis.py coverage gaps: milestone correlation, cooccurrence edge
creation, and failed savepoint recovery."""
import os
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from domain.core.synthesis import SynthesisEngine
from domain.supporting.ledger import StructuralLedger
from domain.core.models import Milestone


class TestMilestoneTemporalCorrelation:
    """Task #20: milestone temporal correlation branch (lines 89-109)."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db = str(tmp_path / "ms_temporal.db")
        semantic = str(tmp_path / "semantic")
        os.makedirs(semantic, exist_ok=True)
        self.engine = SynthesisEngine(semantic, db)
        self.ledger = self.engine.ledger

    def test_milestone_matching_event_creates_edge(self):
        now = datetime.now(timezone.utc)
        # Add a milestone with matching title
        with self.ledger.session_scope() as session:
            ms = Milestone(
                id="ms_test1",
                title="deploy pipeline",
                description="Deployed the CI pipeline",
                timestamp=now,
            )
            session.add(ms)

        # Add a semantic event that mentions the milestone title within the time window
        self.engine.semantic_memory.add_event(
            text="We finished the deploy pipeline today successfully",
            metadata={"type": "milestone", "timestamp": now.isoformat()},
        )

        result = self.engine.run_temporal_correlation_scan()
        assert result >= 1, "Expected edge from milestone→event temporal correlation"

    def test_milestone_outside_time_window_no_edge(self):
        now = datetime.now(timezone.utc)
        old = now - timedelta(hours=3)  # Outside default 60-min window
        with self.ledger.session_scope() as session:
            ms = Milestone(
                id="ms_old",
                title="old milestone",
                timestamp=old,
            )
            session.add(ms)

        self.engine.semantic_memory.add_event(
            text="old milestone is referenced here",
            metadata={"type": "test", "timestamp": now.isoformat()},
        )
        result = self.engine.run_temporal_correlation_scan()
        assert result == 0


class TestCooccurrenceEdgeCreation:
    """Task #21: cooccurrence edge creation with similar events."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db = str(tmp_path / "cooc.db")
        semantic = str(tmp_path / "semantic")
        os.makedirs(semantic, exist_ok=True)
        self.engine = SynthesisEngine(semantic, db)

    def test_similar_events_create_cooccurrence_edge(self):
        now = datetime.now(timezone.utc)
        # Add two very similar events
        self.engine.semantic_memory.add_event(
            text="Learning Python programming for data science applications",
            metadata={"type": "learning", "timestamp": now.isoformat()},
        )
        self.engine.semantic_memory.add_event(
            text="Learning Python programming for data science projects",
            metadata={"type": "learning", "timestamp": now.isoformat()},
        )
        # Mock similarity to return high value
        with patch.object(self.engine.semantic_memory, 'get_similarity', return_value=0.95):
            result = self.engine.run_semantic_cooccurrence_scan()
        assert result >= 1, "Expected cooccurrence edge for highly similar events"


class TestFailedSavepointRecovery:
    """Task #22: force add_edge to raise inside savepoint."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path):
        db = str(tmp_path / "savepoint.db")
        semantic = str(tmp_path / "semantic")
        os.makedirs(semantic, exist_ok=True)
        self.engine = SynthesisEngine(semantic, db)
        self.ledger = self.engine.ledger

    def test_failed_edge_write_does_not_crash_scan(self):
        """If add_edge raises, the scan should continue and not corrupt the session."""
        now = datetime.now(timezone.utc)
        self.ledger.add_skill("python", "programming language")

        self.engine.semantic_memory.add_event(
            text="python is widely used in data science",
            metadata={"type": "learning", "timestamp": now.isoformat()},
        )

        with patch.object(self.ledger, 'add_edge', side_effect=RuntimeError("DB write failed")):
            result = self.engine.run_temporal_correlation_scan()
        # Should not crash; edge count should be 0 since all writes failed
        assert result == 0

    def test_cooccurrence_failed_edge_continues(self):
        """Failed cooccurrence edge write should not crash the scan."""
        now = datetime.now(timezone.utc)
        self.engine.semantic_memory.add_event(
            text="Event alpha about machine learning",
            metadata={"type": "test", "timestamp": now.isoformat()},
        )
        self.engine.semantic_memory.add_event(
            text="Event beta about machine learning",
            metadata={"type": "test", "timestamp": now.isoformat()},
        )

        with patch.object(self.engine.semantic_memory, 'get_similarity', return_value=0.9):
            with patch.object(self.ledger, 'add_edge', side_effect=RuntimeError("constraint")):
                result = self.engine.run_semantic_cooccurrence_scan()
        assert result == 0

    def test_attribute_symmetry_failed_edge_continues(self):
        """Failed symmetry edge write should not crash the scan."""
        self.ledger.add_skill("python scripting", "scripts")
        self.ledger.add_skill("python automation", "automate")

        with patch.object(self.ledger, 'add_edge', side_effect=RuntimeError("DB error")):
            result = self.engine.run_attribute_symmetry_scan()
        assert result == 0
