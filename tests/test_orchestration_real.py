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


@unittest.skipUnless(
    os.environ.get("HERMES_CONFIG_PATH") or os.path.exists("/opt/data/config.yaml"),
    "Requires LLM config"
)
class TestOrchestrationRealLLM(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.real_llm = OpenAIImplementation()
        self.registry = {
            "researcher": ResearcherAgent,
            "auditor": AuditorAgent
        }
        self.orchestrator = Orchestrator(self.registry, self.real_llm)

    async def test_real_llm_goal_execution(self):
        goal = "Audit my recent skill growth"
        result = await self.orchestrator.run_goal(goal, {})
    
        self.assertEqual(result["goal"], goal)
        # Use >= because the LLM might decompose this into more than 2 tasks (e.g., researcher + auditor + something else)
        self.assertGreaterEqual(result["orchestration_summary"]["agents_dispatched"], 2)
        self.assertGreaterEqual(len(result["agent_findings"]), 2)
    
        for finding in result["agent_findings"]:
            self.assertIn("finding", finding)
            self.assertIsInstance(finding["finding"], str)
    
    async def test_single_task_real_llm(self):
        goal = "Describe the essence of pattern recognition."
        result = await self.orchestrator.run_goal(goal, {})
    
        self.assertEqual(result["goal"], goal)
        # Use >= because the LLM might decompose this into multiple sub-tasks for better coverage
        self.assertGreaterEqual(result["orchestration_summary"]["agents_dispatched"], 1)
        self.assertGreaterEqual(len(result["agent_findings"]), 1)
        self.assertIn("finding", result["agent_findings"][0])

if __name__ == '__main__':
    unittest.main()
