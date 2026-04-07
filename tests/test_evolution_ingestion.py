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
from domain.core.semantic_ingestor import SemanticIngestor
from typing import Dict, Any

# A simple Mock LLM for testing orchestration and ingestion
class MockLLM(BaseLLMInterface):
    def complete(self, prompt: str, system_prompt: str = None) -> str:
        if "Synthesize" in prompt or "intelligence" in prompt.lower():
            return "The structural audit confirmed that the ACL layer integration is complete and stable."
        if "Audit" in prompt:
            return "The structural integrity is verified. No issues found."
        if "research" in prompt.lower() or "investigate" in prompt.lower():
            return "The research indicates a major integration milestone was achieved."
        return "Simulated research findings."

async def run_evolution_test():
    print("🧬 Starting THE EVOLUTION TEST (Phase 6.2)... 🧬\n")

    # 1. Setup Infrastructure
    test_dir = os.path.join(root, "tests/evolution_test_db")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    semantic_memory = SemanticMemory(persist_directory=test_dir)
    mock_llm = MockLLM()
    
    # 2. Setup Ingestor and Orchestrator
    ingestor = SemanticIngestor(semantic_memory=semantic_memory, llm=mock_llm)
    
    registry = {
        "researcher": ResearcherAgent,
        "auditor": AuditorAgent
    }
    orchestrator = Orchestrator(registry, llm_interface=mock_llm, ingestor=ingestor)

    # 3. Define the Goal
    complex_goal = "Audit the system and research the recent ACL integration."
    context = {
        "semantic_memory": semantic_memory,
        "context_id": "evolution_test"
    }

    # 4. Execute the Orchestrator
    print(f"🚀 GOAL: {complex_goal}")
    print("-" * 50)
    
    result = await orchestrator.run_goal(complex_goal, context)

    # 5. Validate the Results
    print("-" * 50)
    print("📊 ORCHESTRATION REPORT")
    print(f"Summary: {result['orchestration_summary']}")
    
    print("\n🔍 AGENT FINDINGS:")
    for i, finding in enumerate(result['agent_findings']):
        print(f"[{i+1}] {finding['finding']} (Conf: {finding['confidence']})")

    # 6. VERIFY RECURSIVE INGESTION
    print("\n" + "="*50)
    print("🧠 VERIFYING RECURSIVE INGESTION...")
    print("="*50)
    
    # We search for the synthesized sentence we know the MockLLM will produce
    expected_knowledge = "The structural audit confirmed that the ACL layer integration is complete and stable."
    
    # Perform a semantic search to see if the knowledge was actually added
    search_results = semantic_memory.query(expected_knowledge, limit=1, context_id="evolution_test")
    
    print(f"Searching for: '{expected_knowledge}'")
    if search_results and expected_knowledge in search_results[0]['text']:
        print(f"✅ SUCCESS: Knowledge found in Semantic Memory!")
        print(f"Retrieved Text: {search_results[0]['text']}")
    else:
        print(f"❌ FAILURE: Knowledge NOT found in Semantic Memory.")
        print(f"Found so far: {[r['text'] for r in search_results]}")
        raise ValueError("Recursive ingestion failed to persist knowledge!")

    print("\n🎉 SUCCESS: The Evolution Test is complete! The loop is closed. 🎶")

if __name__ == "__main__":
    asyncio.run(run_evolution_test())
