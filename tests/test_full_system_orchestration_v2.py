import asyncio
import os
import sys
import shutil

# Ensure the project root is in the path
root = os.path.abspath(os.path.dirname(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

from domain.core.semantic_memory import SemanticMemory
from domain.core.agents_impl import ResearcherAgent, AuditorAgent
from application.orchestrator import Orchestrator
from domain.core.ports import BaseLLMInterface
from typing import Dict, Any

# A simple Mock LLM for testing orchestration
class MockLLM(BaseLLMInterface):
    def complete(self, prompt: str, system_prompt: str = None) -> str:
        if "Audit" in prompt:
            return "The structural integrity is verified. No issues found."
        if "research" in prompt.lower() or "investigate" in prompt.lower():
            return "The research indicates a major integration milestone was achieved."
        return "Simulated research findings."

async def run_grand_symphony():
    print("🎻 Starting THE GRAND SYMPHONY TEST... 🎻\n")

    # 1. Setup Infrastructure
    # Using a directory inside the workspace to avoid /tmp permission issues
    test_dir = os.path.join(root, "tests/autonomy_test_db")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    semantic_memory = SemanticMemory(persist_directory=test_dir)
    
    # Seed the memory with some data for the Researcher
    print("[Setup] Seeding Semantic Memory...")
    semantic_memory.add_event(
        "The user successfully integrated the ACL layer into the configuration loader.",
        {"type": "milestone"},
        context_id="development"
    )

    # 2. Setup Orchestrator
    registry = {
        "researcher": ResearcherAgent,
        "auditor": AuditorAgent
    }
    mock_llm = MockLLM()
    orchestrator = Orchestrator(registry, mock_llm)

    # 3. Define the Complex Goal
    complex_goal = "Audit the development context and research the recent integration milestones."
    
    # Construct the context for the agents
    context = {
        "semantic_memory": semantic_memory,
        "context_id": "development",
        "structural_ledger": {"status": "active"} # Mocking the ledger presence
    }

    # 4. Execute the Orchestrator
    print(f"🚀 GOAL: {complex_goal}")
    print("-" * 50)
    
    result = await orchestrator.run_goal(complex_goal, context)

    # 5. Validate the Results
    print("-" * 50)
    print("📊 FINAL ORCHESTRATION REPORT 📊")
    print(f"Goal: {result['goal']}")
    print(f"Summary: {result['orchestration_summary']}")
    
    print("\n🔍 AGENT FINDINGS:")
    for i, finding in enumerate(result['agent_findings']):
        print(f"\n[{i+1}] Status: {finding['status']}")
        print(f"    Confidence: {finding['confidence']}")
        print(f"    Finding: {finding['finding']}")
        if finding['evidence']:
            print(f"    Evidence: {finding['evidence']}")

    # Verification Logic
    assert result['orchestration_summary']['agents_dispatched'] == 2
    assert result['orchestration_summary']['agents_successful'] >= 1
    assert result['orchestration_summary']['aggregate_confidence'] > 0
    
    print("\n✅ SUCCESS: The Grand Symphony was harmonious! 🎶")

if __name__ == "__main__":
    asyncio.run(run_grand_symphony())
