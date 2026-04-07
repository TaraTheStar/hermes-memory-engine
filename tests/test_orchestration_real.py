import os
import sys
import unittest
import asyncio

# Add the repo root to the path
repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, repo_path)

from application.orchestrator import Orchestrator
from infrastructure.llm_implementations import OpenAIImplementation
from domain.core.agents_impl import ResearcherAgent, AuditorAgent

class TestOrchestrationRealLLM(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        print("\n[Setup] Initializing Real LLM Integration...")
        self.real_llm = OpenAIImplementation()
        self.registry = {
            "researcher": ResearcherAgent,
            "auditor": AuditorAgent
        }
        self.orchestrator = Orchestrator(self.registry, self.real_llm)

    async def test_real_llm_goal_execution(self):
        print("\n[Test] Executing goal with real LLM backend...")
        # This goal triggers the decomposition logic in orchestrator.py
        goal = "Audit my recent skill growth"
        
        result = await self.orchestrator.run_goal(goal)
        
        print("\n--- REAL ORCHESTRATION RESULT ---")
        print(result)
        print("----------------------------------")

        self.assertEqual(result["original_goal"], goal)
        self.assertEqual(result["sub_task_count"], 2)
        self.assertEqual(len(result["findings"]), 2)
        
        # Verify that the findings are actual strings (and not error dicts)
        # Verify that the findings are actual strings (and not error dicts)
        for finding in result["findings"]:
            self.assertIn("finding", finding)
            self.assertIsInstance(finding["finding"], str)
            print(f"Finding Response Snippet: {finding['finding'][:100]}...")

    async def test_single_task_real_llm(self):
        print("\n[Test] Executing single task with real LLM backend...")
        goal = "Describe the essence of pattern recognition."
        
        result = await self.orchestrator.run_goal(goal)
        
        print("\n--- REAL SINGLE TASK RESULT ---")
        print(result)
        print("--------------------------------")

        self.assertEqual(result["sub_task_count"], 1)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("finding", result["findings"][0])

if __name__ == '__main__':
    unittest.main()
