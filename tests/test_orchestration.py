import os
import sys
import unittest
import asyncio

# Add the repo root to the path
repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, repo_path)

from application.orchestrator import Orchestrator
from infrastructure.llm_implementations import MockLLMInterface
from domain.core.agents_impl import ResearcherAgent, AuditorAgent

class TestOrchestration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_llm = MockLLMInterface()
        self.registry = {
            "researcher": ResearcherAgent,
            "auditor": AuditorAgent
        }
        self.orchestrator = Orchestrator(self.registry, self.mock_llm)

    async def test_goal_decomposition_and_execution(self):
        # Test a goal that triggers decomposition
        goal = "Audit my recent skill growth"
        result = await self.orchestrator.run_goal(goal)
        
        print("\n--- ORCHESTRATION RESULT ---")
        print(result)
        print("----------------------------")

        self.assertEqual(result["original_goal"], goal)
        self.assertEqual(result["sub_task_count"], 2)
        self.assertEqual(len(result["findings"]), 2)
        
        # Check if findings contain mock responses
        findings_text = str(result["findings"])
        self.assertTrue(any("exploration" in f["finding"].lower() or "integrity" in f["finding"].lower() for f in result["findings"]))
        self.assertTrue(len(result["findings"]) > 0)

    async def test_single_task_goal(self):
        # Test a simple goal that doesn't trigger decomposition
        goal = "What is the current zeitgeist?"
        result = await self.orchestrator.run_goal(goal)
        
        self.assertEqual(result["sub_task_count"], 1)
        self.assertEqual(len(result["findings"]), 1)

if __name__ == '__main__':
    unittest.main()
