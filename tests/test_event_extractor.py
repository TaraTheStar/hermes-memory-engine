import pytest

from application.engine import EventExtractor


@pytest.fixture
def extractor():
    return EventExtractor()


class TestEventExtractor:
    def test_extracts_preference(self, extractor):
        events = extractor.extract_events("I really prefer dark themes")
        assert len(events) >= 1
        assert events[0].event_type == "preference"

    def test_extracts_milestone(self, extractor):
        events = extractor.extract_events("I completed the migration to v2")
        assert len(events) >= 1
        types = [e.event_type for e in events]
        assert "milestone" in types

    def test_extracts_skill(self, extractor):
        events = extractor.extract_events("I learned how to use Kubernetes")
        assert len(events) >= 1
        types = [e.event_type for e in events]
        assert "skill" in types

    def test_extracts_identity(self, extractor):
        events = extractor.extract_events("my name is Alice")
        assert len(events) >= 1
        types = [e.event_type for e in events]
        assert "identity_marker" in types

    def test_high_importance_for_mastered(self, extractor):
        events = extractor.extract_events("I mastered distributed systems")
        assert len(events) >= 1
        high = [e for e in events if e.metadata.get("importance", 0) >= 5.0]
        assert len(high) >= 1

    def test_no_events_from_neutral_text(self, extractor):
        events = extractor.extract_events("The weather is nice today.")
        assert events == []

    def test_case_insensitive(self, extractor):
        events = extractor.extract_events("I LOVE functional programming")
        assert len(events) >= 1


class TestSemanticMemoryGetSimilarity:
    """Test SemanticMemory.get_similarity()."""

    def test_similarity_of_related_events(self, tmp_path):
        from domain.core.semantic_memory import SemanticMemory
        sm = SemanticMemory(str(tmp_path / "sim_test"))
        id1 = sm.add_event("learning Python programming", metadata={"type": "skill"})
        id2 = sm.add_event("studying Python development", metadata={"type": "skill"})
        id3 = sm.add_event("cooking Italian pasta recipes", metadata={"type": "hobby"})

        sim_close = sm.get_similarity(id1, id2)
        sim_far = sm.get_similarity(id1, id3)

        assert sim_close > 0.0
        assert sim_far > 0.0
        # Related events should be more similar than unrelated ones
        assert sim_close > sim_far

    def test_similarity_missing_id(self, tmp_path):
        from domain.core.semantic_memory import SemanticMemory
        sm = SemanticMemory(str(tmp_path / "sim_missing"))
        id1 = sm.add_event("test", metadata={"type": "test"})
        # Nonexistent ID should return 0.0
        result = sm.get_similarity(id1, "nonexistent_id")
        assert result == 0.0
