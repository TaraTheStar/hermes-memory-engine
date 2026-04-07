import asyncio
from typing import List, Dict, Any
from domain.core.agent import HermesAgent, AgentStatus

class Orchestrator:
    """
    The central authority that decomposes goals and manages agent lifecycles.
    """
    def __init__(self, registry: Dict[str, type], llm_interface=None):
        self.registry = registry  # Maps role names to Agent classes
        self.llm = llm_interface
        self.active_agents: List[HermesAgent] = []

    async def decompose_task(self, goal: str) -> List[Dict[str, Any]]:
        """
        Uses the LLM to break a high-level goal into sub-tasks for specific roles.
        """
        # Placeholder for actual LLM decomposition logic
        # In a real implementation, this would call the LLM to return a JSON list of tasks
        print(f"[Orchestrator] Decomposing goal: {goal}")
        
        # Simulated decomposition for testing
        if "audit" in goal.lower():
            return [
                {"role": "auditor", "goal": "Check structural integrity of recent skills", "constraints": ["focus on IDs"]},
                {"role": "researcher", "goal": "Verify semantic relevance of added skills", "constraints": ["use chroma_db"]}
            ]
        return [{"role": "researcher", "goal": goal, "constraints": []}]

    async def run_goal(self, goal: str) -> Dict[str, Any]:
        """
        The main entry point for executing a complex goal.
        """
        tasks = await self.decompose_task(goal)
        results = []

        print(f"[Orchestrator] Dispatched {len(tasks)} sub-tasks.")

        for task in tasks:
            role = task["role"]
            if role in self.registry:
                agent_instance = self.registry[role](f"{role}_{len(self.active_agents)}", role, self.llm)
                self.active_agents.append(agent_instance)
                
                print(f"[Orchestrator] Spawning {agent_instance.agent_id} ({role})...")
                try:
                    # In a real system, this would be truly asynchronous
                    result = await agent_instance.execute(task, {"context": "simulated_context"})
                    results.append(result)
                except Exception as e:
                    print(f"[Orchestrator] Agent {agent_instance.agent_id} failed: {e}")
                    results.append({"error": str(e)})
            else:
                print(f"[Orchestrator] Unknown role: {role}")

        return {
            "original_goal": goal,
            "sub_task_count": len(tasks),
            "findings": results
        }

