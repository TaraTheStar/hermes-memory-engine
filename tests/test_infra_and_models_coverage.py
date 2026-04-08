"""Task #26: Tests for logging_config, models, monitor_models, and ports."""
import logging
import os
import pytest
from unittest.mock import patch
from datetime import datetime, timezone

from domain.core.models import Event, Refinement, RelationalEdge, Base
from domain.supporting.monitor_models import GraphSnapshot, AnomalyEvent, _utc_now


class TestEvent:
    def test_to_dict_structure(self):
        event = Event(
            text="Test event",
            event_type="discovery",
            metadata={"importance": "high", "source": "test"},
        )
        d = event.to_dict()
        assert d["text"] == "Test event"
        assert d["type"] == "discovery"
        assert d["importance"] == "high"
        assert d["source"] == "test"

    def test_to_dict_empty_metadata(self):
        event = Event(text="Simple", event_type="info", metadata={})
        d = event.to_dict()
        assert d == {"text": "Simple", "type": "info"}


class TestMonitorModels:
    def test_utc_now_returns_aware_datetime(self):
        result = _utc_now()
        assert result.tzinfo is not None

    def test_anomaly_event_defaults(self, tmp_path):
        """AnomalyEvent should have sensible defaults."""
        from domain.supporting.ledger import StructuralLedger
        ledger = StructuralLedger(str(tmp_path / "test.db"))
        with ledger.session_scope() as session:
            ae = AnomalyEvent(
                id="ae_test",
                anomaly_type="TEST_TYPE",
                description="Test anomaly",
            )
            session.add(ae)
            session.flush()
            fetched = session.query(AnomalyEvent).get("ae_test")
            assert fetched.severity == "medium"
            assert fetched.processed is False

    def test_graph_snapshot_columns(self, tmp_path):
        from domain.supporting.ledger import StructuralLedger
        ledger = StructuralLedger(str(tmp_path / "snap.db"))
        with ledger.session_scope() as session:
            snap = GraphSnapshot(
                id="snap_1",
                density=0.42,
                community_count=3,
                centrality_metrics={"node_a": {"degree": 0.5}},
            )
            session.add(snap)
            session.flush()
            fetched = session.query(GraphSnapshot).get("snap_1")
            assert fetched.density == 0.42
            assert fetched.community_count == 3
            assert fetched.centrality_metrics["node_a"]["degree"] == 0.5


class TestBaseLLMInterface:
    def test_cannot_instantiate_abstract(self):
        from domain.core.ports.llm_port import BaseLLMInterface
        with pytest.raises(TypeError):
            BaseLLMInterface()


class TestConfigureLogging:
    def test_configure_with_explicit_level(self):
        from infrastructure.logging_config import configure_logging
        # Reset root logger so basicConfig takes effect
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.WARNING)
        logging.root.handlers = []
        configure_logging(level="DEBUG")
        assert root.level == logging.DEBUG

    def test_configure_from_env_var(self):
        from infrastructure.logging_config import configure_logging
        root = logging.getLogger()
        root.handlers.clear()
        logging.root.handlers = []
        with patch.dict(os.environ, {"HERMES_LOG_LEVEL": "WARNING"}):
            configure_logging()
        assert root.level == logging.WARNING

    def test_third_party_loggers_suppressed(self):
        from infrastructure.logging_config import configure_logging
        root = logging.getLogger()
        root.handlers.clear()
        logging.root.handlers = []
        configure_logging(level="DEBUG")
        assert logging.getLogger("chromadb").level == logging.WARNING
        assert logging.getLogger("httpx").level == logging.WARNING
        assert logging.getLogger("openai").level == logging.WARNING
