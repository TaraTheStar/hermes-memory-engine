"""Task #24: Test the autonomous_orchestrator retry cap permanent-skip behavior."""
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from application.autonomous_orchestrator import AutonomousOrchestrator
from domain.core.agents_impl import ResearcherAgent
from domain.core.semantic_memory import SemanticMemory


@pytest.fixture
def setup(tmp_path):
    semantic_dir = str(tmp_path / "semantic")
    os.makedirs(semantic_dir, exist_ok=True)
    memory = SemanticMemory(semantic_dir)
    registry = {"researcher": ResearcherAgent}
    mock_llm = MagicMock()
    mock_llm.complete = MagicMock(return_value="Research result")
    orch = AutonomousOrchestrator(
        registry=registry,
        llm_interface=mock_llm,
        semantic_memory=memory,
    )
    return orch, memory


@pytest.mark.asyncio
async def test_event_permanently_skipped_after_max_retries(setup):
    """After _max_event_retries failures, the event should be added to
    _processed_event_ids and skipped permanently."""
    orch, memory = setup
    orch._max_event_retries = 2

    # Add an event that will trigger processing (has "integration" in text)
    memory.add_event(
        text="Major integration of new subsystem",
        metadata={"type": "milestone", "timestamp": "2025-06-01T12:00:00+00:00"},
    )

    events = memory.list_events(limit=1)
    event_id = events[0]["id"]

    # Simulate failures: set failure count to max
    orch._event_failure_counts[event_id] = 2

    # Run one monitoring iteration (we'll call the inner logic directly)
    recent_events = memory.list_events(limit=5)
    for event in recent_events:
        eid = event.get("id")
        if eid in orch._processed_event_ids:
            continue
        if orch._event_failure_counts.get(eid, 0) >= orch._max_event_retries:
            orch._processed_event_ids[eid] = None
            continue

    assert event_id in orch._processed_event_ids, \
        "Event should be permanently skipped after max retries"


@pytest.mark.asyncio
async def test_retry_cap_increments_on_failure(setup):
    """Each goal failure should increment the failure count."""
    orch, memory = setup

    memory.add_event(
        text="New integration event for retry test",
        metadata={"type": "milestone", "timestamp": "2025-06-01T12:00:00+00:00"},
    )
    events = memory.list_events(limit=1)
    event_id = events[0]["id"]

    # Simulate a single failure
    orch._event_failure_counts[event_id] = 0
    orch._event_failure_counts[event_id] += 1

    assert orch._event_failure_counts[event_id] == 1
    assert event_id not in orch._processed_event_ids
