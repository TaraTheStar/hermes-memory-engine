import datetime
from abc import ABC, abstractmethod
from datetime import timezone
from typing import Dict, Any, Optional, List, Protocol
from domain.core.ports import BaseLLMInterface

class AgentStatus:
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    REFLECTING = "reflecting"
    REPORTING = "reporting"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentTask:
    """Represents a single unit of work for an agent."""
    def __init__(self, goal: str, constraints: Optional[List[str]] = None):
        self.goal = goal
        self.constraints = constraints or []
        self.created_at = datetime.datetime.now(timezone.utc)

from typing import Dict, Any, Optional, List, Protocol, Union

class RefinementProposal:
    """Represents a self-optimization proposal from an agent."""
    PROMPT_REFINEMENT = "PROMPT_REFINEMENT"
    TOOL_EXPANSION = "TOOL_EXPANSION"

    def __init__(self, 
                 proposal_type: str, 
                 target_component: str, 
                 current_state: str, 
                 proposed_state: str, 
                 rationale: str):
        self.proposal_type = proposal_type  # 'PROMPT_REFINEMENT' | 'TOOL_EXPANSION'
        self.target_component = target_component
        self.current_state = current_state
        self.proposed_state = proposed_state
        self.rationale = rationale

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.proposal_type,
            "target": self.target_component,
            "current": self.current_state,
            "proposed": self.proposed_state,
            "rationale": self.rationale
        }

class RefinementType:
    PROMPT_REFINEMENT = "PROMPT_REFINEMENT"
    TOOL_EXPANSION = "TOOL_EXPANSION"

class AgentResult:
    """Represents the outcome of an agent's execution."""
    def __init__(self, 
                 finding: str, 
                 confidence: float, 
                 evidence: List[Dict[str, Any]], 
                 status: str = AgentStatus.COMPLETED,
                 refinement_proposal: Optional[RefinementProposal] = None):
        self.finding = finding
        self.confidence = confidence
        self.evidence = evidence
        self.status = status
        self.refinement_proposal = refinement_proposal
        self.completed_at = datetime.datetime.now(timezone.utc)

class HermesAgent(ABC):
    """
    The abstract base class for all specialized agents within the Hermes ecosystem.
    Implements the core Agentic Lifecycle: Observe -> Plan -> Act -> Reflect.
    """
    def __init__(self, agent_id: str, role: str, llm: BaseLLMInterface):
        self.agent_id = agent_id
        self.role = role
        self.llm = llm
        self.status = AgentStatus.IDLE
        self.history: List[Dict[str, Any]] = []
        self.current_task: Optional[AgentTask] = None

    async def run(self, task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        """
        The primary execution lifecycle for an agent.

        State transitions:
            IDLE -> THINKING -> ACTING -> REFLECTING -> REPORTING -> COMPLETED
                    \____________any stage____________/ -> FAILED (on exception)

        Stages:
            THINKING:    _plan() decomposes the goal into sub-tasks.
            ACTING:      _execute_plan() runs each sub-task via the LLM.
            REFLECTING:  _reflect() evaluates findings against the goal/constraints.
            REPORTING:   Final result is logged; status moves to COMPLETED.
        """
        self.current_task = task
        self._log(f"Starting task: {task.goal}")
        
        try:
            # 1. THINKING (Plan)
            self.status = AgentStatus.THINKING
            plan = await self._plan(task, context)
            self._log(f"Plan generated: {plan}")

            # 2. ACTING (Execute)
            self.status = AgentStatus.ACTING
            raw_findings = await self._execute_plan(plan, context)
            self._log("Execution complete.")

            # 3. REFLECTING (Evaluate)
            self.status = AgentStatus.REFLECTING
            final_result = await self._reflect(raw_findings, task, context)
            self._log("Reflection complete.")

            # 4. REPORTING
            self.status = AgentStatus.REPORTING
            self._log(f"Task completed with confidence {final_result.confidence}")
            self.status = AgentStatus.COMPLETED
            
            return final_result

        except Exception as e:
            self.status = AgentStatus.FAILED
            self._log(f"Agent execution failed: {str(e)}", level="ERROR")
            return AgentResult(
                finding=f"Execution failed: {str(e)}",
                confidence=0.0,
                evidence=[],
                status=AgentStatus.FAILED
            )

    @abstractmethod
    async def _plan(self, task: AgentTask, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Decomposes a goal into a sequence of sub-tasks/actions."""
        pass

    @abstractmethod
    async def _execute_plan(self, plan: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Executes the planned sub-tasks."""
        pass

    @abstractmethod
    async def _reflect(self, findings: List[Dict[str, Any]], task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        """Refines findings and ensures they meet the task goal and constraints."""
        pass

    def _log(self, message: str, level: str = "INFO"):
        self.history.append({
            "timestamp": datetime.datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
            "status": self.status
        })
