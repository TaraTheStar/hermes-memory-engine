import os
import pytest

from application.orchestrator import Orchestrator
from infrastructure.llm_implementations import OpenAIImplementation
from domain.core.agents_impl import ResearcherAgent, AuditorAgent

pytestmark = pytest.mark.skipif(
    not (os.environ.get("HERMES_HOME") or os.path.isfile(os.path.expanduser("~/.hermes/config.yaml"))),
    reason="Requires LLM config (set HERMES_HOME or ensure ~/.hermes/config.yaml exists)",
)


@pytest.fixture
def orchestrator():
    real_llm = OpenAIImplementation()
    registry = {
        "researcher": ResearcherAgent,
        "auditor": AuditorAgent,
    }
    return Orchestrator(registry, real_llm)


@pytest.mark.asyncio
async def test_real_llm_goal_execution(orchestrator):
    goal = "Audit my recent skill growth"
    result = await orchestrator.run_goal(goal, {})

    assert result["goal"] == goal
    assert result["orchestration_summary"]["agents_dispatched"] >= 2
    assert len(result["agent_findings"]) >= 2

    for finding in result["agent_findings"]:
        assert "finding" in finding
        assert isinstance(finding["finding"], str)


@pytest.mark.asyncio
async def test_single_task_real_llm(orchestrator):
    goal = "Describe the essence of pattern recognition."
    result = await orchestrator.run_goal(goal, {})

    assert result["goal"] == goal
    assert result["orchestration_summary"]["agents_dispatched"] >= 1
    assert len(result["agent_findings"]) >= 1
    assert "finding" in result["agent_findings"][0]
