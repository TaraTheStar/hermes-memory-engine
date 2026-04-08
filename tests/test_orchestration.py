import pytest

from application.orchestrator import Orchestrator
from infrastructure.llm_implementations import MockLLMInterface
from domain.core.agents_impl import ResearcherAgent, AuditorAgent


@pytest.fixture
def orchestrator():
    mock_llm = MockLLMInterface()
    registry = {
        "researcher": ResearcherAgent,
        "auditor": AuditorAgent,
    }
    return Orchestrator(registry, mock_llm)


@pytest.mark.asyncio
async def test_goal_decomposition_and_execution(orchestrator):
    """Test a goal that triggers decomposition into 2 agents (audit triggers researcher + auditor)."""
    goal = "Audit my recent skill growth"
    result = await orchestrator.run_goal(goal, {})

    assert result["goal"] == goal
    assert result["orchestration_summary"]["agents_dispatched"] == 2
    assert len(result["agent_findings"]) == 2


@pytest.mark.asyncio
async def test_single_task_goal(orchestrator):
    """Test a simple goal that doesn't trigger decomposition (falls back to single researcher)."""
    goal = "What is the current zeitgeist?"
    result = await orchestrator.run_goal(goal, {})

    assert result["orchestration_summary"]["agents_dispatched"] == 1
    assert len(result["agent_findings"]) == 1
