import asyncio
import logging
from typing import Dict, Any, List, Optional, Type
import asyncio
import logging
from typing import Dict, Any, List, Optional, Type
from domain.core.agent import HermesAgent, AgentStatus, AgentTask, AgentResult
from domain.core.ports.ingestor import IntelligenceIngestor

class Orchestrator:
    """
    The central authority that decomposes goals and manages agent lifecycles.
    Acts as the Conductor of the multi-agent system.
    """
    def __init__(self, registry: Dict[str, Type[HermesAgent]], llm_interface=None, ingestor: Optional[IntelligenceIngestor] = None):
        self.registry = registry  # Maps role names to Agent classes
        self.llm = llm_interface
        self.active_agents: List[HermesAgent] = []
        self.ingestor = ingestor

    async def decompose_task(self, goal: str) -> List[Dict[str, Any]]:
        """
        Uses the LLM to break a high-level goal into sub-tasks for specific roles.
        
        In a full implementation, this uses an LLM with a strict JSON schema.
        For this implementation, we provide a robust simulated decomposition.
        """
        print(f"[Orchestrator] Decomposing goal: '{goal}'")
        
        # Simulated LLM-driven decomposition logic
        goal_lower = goal.lower()
        
        if "audit" in goal_lower or "verify" in goal_lower:
            return [
                {
                    "role": "auditor", 
                    "goal": "Validate the structural integrity of the target entity.", 
                    "constraints": ["check existence", "validate relationship"]
                },
                {
                    "role": "researcher", 
                    "goal": "Investigate semantic context and background information.", 
                    "constraints": ["retrieve historical evidence"]
                }
            ]
        elif "research" in goal_lower or "find" in goal_lower:
            return [
                {
                    "role": "researcher", 
                    "goal": f"Conduct deep dive into: {goal}", 
                    "constraints": ["provide high-confidence evidence"]
                }
            ]
        
        # Default fallback
        return [{"role": "researcher", "goal": goal, "constraints": []}]

    async def run_goal(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        The main entry point for executing a complex goal.
        Manages the parallel execution and synthesis of agent results.
        """
        tasks_data = await self.decompose_task(goal)
        
        # Convert task dicts into formal AgentTask objects
        tasks = [AgentTask(t["goal"], t["constraints"]) for t in tasks_data]
        
        print(f"[Orchestrator] Dispatched {len(tasks)} sub-tasks.")
        
        # Prepare the agent coroutines for parallel execution
        agent_tasks = []
        
        for i, task in enumerate(tasks):
            role = tasks_data[i]["role"]
            if role in self.registry:
                # Instantiate the agent
                agent_id = f"{role}_{i:02d}"
                agent_instance = self.registry[role](agent_id, role, self.llm)
                self.active_agents.append(agent_instance)
                
                print(f"[Orchestrator] Spawning {agent_instance.agent_id} ({role})...")
                
                # Schedule the agent's run method
                agent_tasks.append(self._execute_agent(agent_instance, task, context))
            else:
                print(f"[Orchestrator] Unknown role: {role}")

        # Execute all agents concurrently
        raw_results = await asyncio.gather(*agent_tasks)
        
        # Synthesize findings
        final_report = self._synthesize(goal, raw_results)
        
        # --- NEW: Recursive Learning Step ---
        if self.ingestor:
            print(f"[Orchestrator] Triggering Intelligence Ingestion for goal: '{goal}'")
            # We pass the final_report and the context to the ingestor
            success = await self.ingestor.ingest(final_report, context)
            if success:
                print(f"[Orchestrator] 🧠 Learning successful: Findings ingested into Semantic Memory.")
            else:
                print(f"[Orchestrator] ⚠️ Learning failed: Ingestion unsuccessful.")
        # ------------------------------------
        
        return final_report

    async def _execute_agent(self, agent: HermesAgent, task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        """Helper to run an agent and catch any lifecycle failures."""
        try:
            return await agent.run(task, context)
        except Exception as e:
            print(f"[Orchestrator] Fatal error in agent {agent.agent_id}: {e}")
            return AgentResult(
                finding=f"Agent failure: {str(e)}",
                confidence=0.0,
                evidence=[],
                status=AgentStatus.FAILED
            )

    def _synthesize(self, goal: str, results: List[AgentResult]) -> Dict[str, Any]:
        """
        Combines the findings from multiple agents into a single, coherent narrative.
        """
        print("[Orchestrator] Synthesizing agent findings...")
        
        findings = []
        total_confidence = 0.0
        successful_agents = 0

        for res in results:
            findings.append({
                "finding": res.finding,
                "confidence": res.confidence,
                "evidence": res.evidence,
                "status": res.status
            })
            
            if res.status in [AgentStatus.COMPLETED, AgentStatus.REPORTING]:
                total_confidence += res.confidence
                successful_agents += 1

        avg_confidence = (total_confidence / successful_agents) if successful_agents > 0 else 0.0

        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }


        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }

        avg_confidence = (total_confidence / successful_agents) if successful_agents > 0 else 0.0

        return {
            "goal": goal,
            "orchestration_summary": {
                "agents_dispatched": len(results),
                "agents_successful": successful_agents,
                "aggregate_confidence": round(avg_confidence, 2)
            },
            "agent_findings": findings
        }

