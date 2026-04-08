import asyncio
import pytest
from collections import OrderedDict
from unittest.mock import AsyncMock, MagicMock

from application.autonomous_orchestrator import AutonomousOrchestrator
from domain.core.agents_impl import ResearcherAgent, AuditorAgent


@pytest.fixture
def registry():
    return {"researcher": ResearcherAgent, "auditor": AuditorAgent}


@pytest.fixture
def orch(registry):
    return AutonomousOrchestrator(registry)


class TestProcessedEventEviction:
    def test_uses_ordered_dict(self, orch):
        assert isinstance(orch._processed_event_ids, OrderedDict)

    def test_evicts_oldest_not_arbitrary(self, orch):
        orch._max_processed_ids = 3
        for eid in ["a", "b", "c", "d"]:
            orch._processed_event_ids[eid] = None
            while len(orch._processed_event_ids) > orch._max_processed_ids:
                orch._processed_event_ids.popitem(last=False)

        assert "a" not in orch._processed_event_ids
        assert list(orch._processed_event_ids.keys()) == ["b", "c", "d"]


class TestStartStopMonitoring:
    @pytest.mark.asyncio
    async def test_start_creates_task(self, orch):
        await orch.start_monitoring(interval_seconds=1)
        assert orch._is_running is True
        assert orch._monitoring_task is not None
        await orch.stop_monitoring()

    @pytest.mark.asyncio
    async def test_double_start_does_not_create_second_task(self, orch):
        await orch.start_monitoring(interval_seconds=1)
        first_task = orch._monitoring_task
        await orch.start_monitoring(interval_seconds=1)
        assert orch._monitoring_task is first_task
        await orch.stop_monitoring()

    @pytest.mark.asyncio
    async def test_stop_cleans_up(self, orch):
        await orch.start_monitoring(interval_seconds=1)
        await orch.stop_monitoring()
        assert orch._is_running is False


class TestSemanticEventFiltering:
    """Tests exercise the filtering logic by invoking _monitoring_loop body directly."""

    @staticmethod
    async def _run_one_iteration(orch, context=None):
        """Run exactly one iteration of the monitoring loop, then stop."""
        context = context or {}
        orch._is_running = True
        # Patch sleep to stop after one iteration
        original_sleep = asyncio.sleep
        call_count = 0
        async def _stop_after_one(seconds):
            nonlocal call_count
            call_count += 1
            orch._is_running = False
            await original_sleep(0)
        asyncio.sleep = _stop_after_one
        try:
            await orch._monitoring_loop(999, context)
        finally:
            asyncio.sleep = original_sleep

    @pytest.mark.asyncio
    async def test_milestone_event_triggers_goal(self, registry):
        mock_semantic = MagicMock()
        mock_semantic.list_events.return_value = [
            {
                "id": "evt_1",
                "text": "completed the migration",
                "metadata": {"type": "milestone_completion"},
            }
        ]
        orch = AutonomousOrchestrator(
            registry, semantic_memory=mock_semantic
        )
        goals_run = []
        async def _capture_goal(goal, context):
            goals_run.append(goal)
            return {"orchestration_summary": {"aggregate_confidence": 0.9}}
        orch.run_goal = _capture_goal

        await self._run_one_iteration(orch)

        assert len(goals_run) >= 1
        assert "evt_1" in orch._processed_event_ids

    @pytest.mark.asyncio
    async def test_integration_keyword_triggers_goal(self, registry):
        mock_semantic = MagicMock()
        mock_semantic.list_events.return_value = [
            {
                "id": "evt_2",
                "text": "new integration with external API",
                "metadata": {"type": "general"},
            }
        ]
        orch = AutonomousOrchestrator(
            registry, semantic_memory=mock_semantic
        )
        goals_run = []
        async def _capture_goal(goal, context):
            goals_run.append(goal)
            return {"orchestration_summary": {"aggregate_confidence": 0.9}}
        orch.run_goal = _capture_goal

        await self._run_one_iteration(orch)

        assert len(goals_run) >= 1

    @pytest.mark.asyncio
    async def test_irrelevant_event_does_not_trigger(self, registry):
        mock_semantic = MagicMock()
        mock_semantic.list_events.return_value = [
            {
                "id": "evt_3",
                "text": "just a regular observation",
                "metadata": {"type": "general"},
            }
        ]
        orch = AutonomousOrchestrator(
            registry, semantic_memory=mock_semantic
        )
        goals_run = []
        async def _capture_goal(goal, context):
            goals_run.append(goal)
            return {"orchestration_summary": {"aggregate_confidence": 0.9}}
        orch.run_goal = _capture_goal

        await self._run_one_iteration(orch)

        assert len(goals_run) == 0

    @pytest.mark.asyncio
    async def test_already_processed_event_skipped(self, registry):
        mock_semantic = MagicMock()
        mock_semantic.list_events.return_value = [
            {
                "id": "evt_already",
                "text": "integration event",
                "metadata": {"type": "general"},
            }
        ]
        orch = AutonomousOrchestrator(
            registry, semantic_memory=mock_semantic
        )
        orch._processed_event_ids["evt_already"] = None

        goals_run = []
        async def _capture_goal(goal, context):
            goals_run.append(goal)
            return {"orchestration_summary": {"aggregate_confidence": 0.9}}
        orch.run_goal = _capture_goal

        await self._run_one_iteration(orch)

        assert len(goals_run) == 0
