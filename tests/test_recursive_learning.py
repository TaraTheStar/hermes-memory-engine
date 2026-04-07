import asyncio
import os
import sys
import shutil

# Ensure the project root is in the path
root = os.path.abspath(os.path.dirname(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

from domain.core.agent import HermesAgent, AgentStatus, AgentTask, AgentResult
from domain.core.semantic_memory import SemanticMemory
from domain.core.semantic_ingestor import SemanticIngestor
from domain.core.ports import BaseLLMInterface
from application.orchestrator import Orchestrator
from typing import Dict, Any, List

# 1. Mock LLM
class MockLLM(BaseLLMInterface):
    async def complete(self, prompt: str, system_prompt: str = None) -> str:
        # The prompt for synthesis will contain "SYNTHESIZED EVENT:"
        if "SYNTHESIZED EVENT:" in prompt:
            return "The integration of the ACL layer was successfully completed and verified across all modules."
        return "Simulated research findings."

# 2. Mock Agents for the registry
class MockResearcher(HermesAgent):
    async def _plan(self, task, context): return [{"role": "researcher", "goal": task.goal, "constraints": []}]
    async def _execute_plan(self, plan, context): return [{"finding": "ACL layer is fully integrated.", "confidence": 0.9, "evidence": [], "status": AgentStatus.COMPLETED}]
    async def _reflect(self, findings, task, context): return AgentResult(findings[0]["finding"], findings[0]["confidence"], findings[0]["evidence"])

class MockAuditor(HermesAgent):
    async def _plan(self, task, context): return [{"role": "auditor", "goal": task.goal, "constraints": []}]
    async def _execute_plan(self, plan, context): return [{"finding": "Integration verified with 100% success.", "confidence": 0.95, "evidence": [], "status": AgentStatus.COMPLETED}]
    async def _reflect(self, findings, task, context): return AgentResult(findings[0]["finding"], findings[0]["confidence"], findings[0]["evidence"])

async def run_evolution_test():
    print("🧬 Starting THE EVOLUTION TEST (Phase 6.2)... 🧬\n")

    # Setup
    test_dir = os.path.join(root, "tests/evolution_test_db")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    sm = SemanticMemory(persist_directory=test_dir)
    mock_llm = MockLLM()
    ingestor = SemanticIngestor(semantic_memory=sm, llm=mock_llm)
    
    registry = {
        "researcher": MockResearcher,
        "auditor": MockAuditor
    }
    
    orch = Orchestrator(registry=registry, llm_interface=mock_llm, ingestor=ingestor)

    # 3. Execute Goal
    goal = "Investigate the recent integration of the ACL layer."
    print(f"🚀 GOAL: {goal}")
    print("-" * 50)
    
    result = await orch.run_goal(goal, context={"context_id": "evolution_test"})

    print("-" * 50)
    print("📊 ORCHESTRATION REPORT RECEIVED.")
    print(f"Summary: {result['orchestration_summary']}")

    # 4. Verify Ingestion
    print("\n🔍 VERIFYING RECURSIVE LEARNING...")
    
    # Search for the synthesized knowledge
    search_query = "ACL layer integration"
    print(f"Searching memory for: '{search_query}'")
    
    # Use semantic search
    search_results = sm.search(search_query, context_id="evolution_test", limit=1)
    
    if search_results:
        print("\n✅ SUCCESS: Knowledge found in long-term memory!")
        print(f"Found Event: \"{search_results[0]['text']}\"")
        print(f"Metadata: {search_results[0]['metadata']}")
    else:
        print("\n❌ FAILURE: Knowledge was not found in memory.")
        # Debug: list all events
        all_events = sm.list_events(limit=10)
        print(f"Current events in memory: {all_events}")
        sys.exit(1)

    print("\n🧬 EVOLUTION COMPLETE: The system has learned from its actions. 🧬")

if __name__ == "__main__":
    asyncio.run(run_evolution_test())
