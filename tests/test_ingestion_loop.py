import asyncio
import os
import shutil
import sys

# Ensure the project root is in the path
root = "/data/workspace/repos/hermes-memory-library"
if root not in sys.path:
    sys.path.insert(0, root)

from domain.core.semantic_memory import SemanticMemory
from domain.core.agents_impl import ResearcherAgent
from application.orchestrator import Orchestrator
from domain.core.ports import BaseLLMInterface
from domain.core.semantic_ingestor import SemanticIngestor
from domain.core.ports.ingestor import IntelligenceIngestor

class MockLLM(BaseLLMInterface):
    def complete(self, prompt: str, system_prompt: str = None) -> str:
        return "The integration of the new module was successful and enhanced system connectivity."

async def verify_ingestion():
    print("🧪 Starting Small Ingestion Test...")
    
    test_dir = os.path.join(root, "tests/ingestion_test_db")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    # 1. Setup
    sm = SemanticMemory(persist_directory=test_dir)
    mock_llm = MockLLM()
    ingestor = SemanticIngestor(semantic_memory=sm, llm=mock_llm)
    
    registry = {"researcher": ResearcherAgent}
    orch = Orchestrator(registry=registry, llm_interface=mock_llm, ingestor=ingestor)

    # 2. Execute Goal
    goal = "Research the importance of module integration."
    print(f"🚀 Running goal: {goal}")
    
    # We pass the context needed for ingestion
    context = {"context_id": "test_context"}
    await orch.run_goal(goal, context)

    # 3. Verify
    print("🔍 Checking memory for synthesized knowledge...")
    events = sm.list_events(limit=1)
    
    if events:
        print(f"✅ SUCCESS! Found ingested event: '{events[0]['text']}'")
        assert "integration" in events[0]['text'].lower()
    else:
        print("❌ FAILURE: No events found in memory after orchestration.")
        sys.exit(1)

    # Cleanup
    shutil.rmtree(test_dir)
    print("🎉 Test Complete!")

if __name__ == "__main__":
    asyncio.run(verify_ingestion())
