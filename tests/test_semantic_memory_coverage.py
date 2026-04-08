"""Task #25: Test semantic_memory.list_events_by_context and related gaps."""
import os
import pytest
from domain.core.semantic_memory import SemanticMemory


@pytest.fixture
def memory(tmp_path):
    d = str(tmp_path / "semantic")
    os.makedirs(d, exist_ok=True)
    return SemanticMemory(d)


class TestListEventsByContext:
    def test_filters_by_context(self, memory):
        """list_events_by_context should only return events matching context_id."""
        memory.add_event(
            text="Event in context A",
            metadata={"type": "test", "timestamp": "2025-01-01T00:00:00+00:00"},
            context_id="ctx_a",
        )
        memory.add_event(
            text="Event in context B",
            metadata={"type": "test", "timestamp": "2025-01-01T00:01:00+00:00"},
            context_id="ctx_b",
        )
        memory.add_event(
            text="Another event in context A",
            metadata={"type": "test", "timestamp": "2025-01-01T00:02:00+00:00"},
            context_id="ctx_a",
        )

        results = memory.list_events_by_context("ctx_a", limit=10)
        assert len(results) == 2
        for r in results:
            assert r["metadata"]["context_id"] == "ctx_a"

    def test_returns_empty_for_unknown_context(self, memory):
        memory.add_event(
            text="Some event",
            metadata={"type": "test", "timestamp": "2025-01-01T00:00:00+00:00"},
            context_id="ctx_x",
        )
        results = memory.list_events_by_context("nonexistent", limit=10)
        assert results == []

    def test_respects_limit(self, memory):
        for i in range(5):
            memory.add_event(
                text=f"Event {i}",
                metadata={"type": "test", "timestamp": f"2025-01-01T00:0{i}:00+00:00"},
                context_id="ctx_limited",
            )
        results = memory.list_events_by_context("ctx_limited", limit=2)
        assert len(results) == 2
