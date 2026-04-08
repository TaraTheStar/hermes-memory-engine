import asyncio
import logging
from collections import OrderedDict
from typing import Dict, Any, List, Optional, Set, Type
from application.orchestrator import Orchestrator
from domain.core.agent import HermesAgent, AgentStatus
from domain.core.ports import GoalRunner
from domain.core.ports.ingestor import IntelligenceIngestor
from domain.core.refinement_registry import RefinementRegistry
from domain.core.semantic_memory import SemanticMemory
from domain.core.insight_trigger import InsightTrigger
from domain.supporting.ledger import StructuralLedger

logger = logging.getLogger(__name__)

class AutonomousOrchestrator(Orchestrator, GoalRunner):
    """
    An extension of the Orchestrator that can initiate its own investigation goals
    based on environmental stimuli (anomalies, new memory, structural changes).
    """
    def __init__(self, registry: Dict[str, Type[HermesAgent]], llm_interface=None,
                 semantic_memory: Optional[SemanticMemory] = None,
                 structural_ledger: Optional[StructuralLedger] = None,
                 insight_trigger: Optional[InsightTrigger] = None,
                 ingestor: Optional[IntelligenceIngestor] = None):
        # Wire up a persistent RefinementRegistry when a ledger is available
        refinement_registry = RefinementRegistry(structural_ledger) if structural_ledger else None
        super().__init__(registry, llm_interface, ingestor=ingestor,
                         refinement_registry=refinement_registry)
        self.semantic_memory = semantic_memory
        self.structural_ledger = structural_ledger
        self.insight_trigger = insight_trigger
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_running = False
        self._processed_event_ids: OrderedDict[str, None] = OrderedDict()
        self._max_processed_ids = 10000
        self._event_failure_counts: Dict[str, int] = {}
        self._max_event_retries = 3
        self._consecutive_errors = 0
        self._max_consecutive_errors = 5
        self._start_lock = asyncio.Lock()

    async def start_monitoring(self, interval_seconds: int = 300, context: Dict[str, Any] = None):
        """Starts the background monitoring loop."""
        async with self._start_lock:
            if self._is_running:
                logger.warning("Monitoring is already running.")
                return

            self._is_running = True
            self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval_seconds, context or {}))
        logger.info(f"Autonomous monitoring started with {interval_seconds}s interval.")

    async def stop_monitoring(self):
        """Stops the background monitoring loop."""
        self._is_running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Autonomous monitoring stopped.")

    async def _monitoring_loop(self, interval_seconds: int, context: Dict[str, Any]):
        """The core loop of the autonomous agent."""
        while self._is_running:
            try:
                logger.info("Scanning environment for triggers...")

                # 1. Check for anomalies via InsightTrigger
                if self.insight_trigger:
                    await self.insight_trigger.process_new_anomalies(context)

                # 2. Check for new semantic intelligence
                if self.semantic_memory:
                    recent_events = self.semantic_memory.list_events(limit=5)
                    if recent_events:
                        for event in recent_events:
                            event_id = event.get('id')
                            if event_id in self._processed_event_ids:
                                continue
                            if self._event_failure_counts.get(event_id, 0) >= self._max_event_retries:
                                logger.warning("Event %s failed %d times, skipping permanently.", event_id, self._max_event_retries)
                                self._processed_event_ids[event_id] = None
                                continue
                            metadata = event.get('metadata') or {}
                            if "milestone" in metadata.get('type', '') or "integration" in event['text'].lower():
                                from domain.core.prompt_sanitizer import sanitize_field
                                goal = f"Investigate the recent semantic milestone: {sanitize_field(event['text'], 'event_text')}"
                                logger.info(f"Trigger detected! New Goal: {goal}")
                                try:
                                    await self.run_goal(goal, context)
                                    self._processed_event_ids[event_id] = None
                                except Exception as goal_err:
                                    self._event_failure_counts[event_id] = self._event_failure_counts.get(event_id, 0) + 1
                                    logger.warning("Goal for event %s failed (attempt %d/%d): %s",
                                                   event_id, self._event_failure_counts[event_id], self._max_event_retries, goal_err)
                                    continue
                                # Evict oldest IDs to prevent unbounded growth
                                while len(self._processed_event_ids) > self._max_processed_ids:
                                    self._processed_event_ids.popitem(last=False)

                # 3. Check for structural changes
                if self.structural_ledger:
                    # Simulate a structural anomaly check
                    pass

                self._consecutive_errors = 0
                # Wait for the next interval
                await asyncio.sleep(interval_seconds)

            except Exception as e:
                self._consecutive_errors += 1
                logger.error("Error in monitoring loop (%d/%d): %s",
                             self._consecutive_errors, self._max_consecutive_errors, e)
                if self._consecutive_errors >= self._max_consecutive_errors:
                    logger.critical("Circuit breaker tripped: %d consecutive errors. Stopping monitoring.",
                                    self._consecutive_errors)
                    self._is_running = False
                    break
                # Exponential backoff capped at the normal interval
                backoff = min(5 * (2 ** (self._consecutive_errors - 1)), interval_seconds)
                await asyncio.sleep(backoff)

    async def run_goal(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Implementation of the GoalRunner protocol.
        Extends run_goal to include autonomous-specific logging.
        """
        logger.info(f"🚀 EXECUTING AUTONOMOUS GOAL: {goal}")
        result = await super().run_goal(goal, context)
        logger.info(f"✅ AUTONOMOUS GOAL COMPLETED. Confidence: {result.get('orchestration_summary', {}).get('aggregate_confidence', 0)}")
        return result
