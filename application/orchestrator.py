import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Type
from domain.core.agent import HermesAgent, AgentStatus, AgentTask, AgentResult
from domain.core.ports.ingestor import IntelligenceIngestor
from domain.core.refinement_registry import RefinementRegistry
from domain.core.prompt_sanitizer import sanitize_field

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    The central authority that decomposes goals and manages agent lifecycles.
    Acts as the Conductor of the multi-agent system.
    """
    def __init__(self, registry: Dict[str, Type[HermesAgent]], llm_interface=None, ingestor: Optional[IntelligenceIngestor] = None, refinement_registry: Optional[RefinementRegistry] = None):
        self.registry = registry  # Maps role names to Agent classes
        self.llm = llm_interface
        self.active_agents: List[HermesAgent] = []
        self._agents_lock = asyncio.Lock()
        self._max_concurrent_agents = 10
        self.ingestor = ingestor
        self.refinement_registry = refinement_registry or RefinementRegistry()

    def register_agent_role(self, role_name: str, agent_class: Type[HermesAgent]):
        """Dynamically adds a new agent role to the orchestrator's registry."""
        logger.info("Registering new agent role: '%s'", role_name)
        self.registry[role_name] = agent_class

    async def decompose_task(self, goal: str) -> List[Dict[str, Any]]:
        """
        Breaks a high-level goal into sub-tasks for specific agent roles.

        When an LLM is configured, it is used to generate the decomposition.
        Otherwise, falls back to keyword-based heuristic routing.
        """
        logger.info("Decomposing goal: '%s'", goal)

        if self.llm:
            return await self._llm_decompose(goal)

        return self._heuristic_decompose(goal)

    _LLM_DECOMPOSE_MAX_RETRIES = 2

    async def _llm_decompose(self, goal: str) -> List[Dict[str, Any]]:
        """Uses the LLM to decompose a goal into role-tagged sub-tasks.

        Retries up to ``_LLM_DECOMPOSE_MAX_RETRIES`` times on transient
        failures before falling back to heuristic decomposition.
        """
        available_roles = list(self.registry.keys())
        prompt = "Break the following goal into sub-tasks. "
        prompt += "Available agent roles: " + str(available_roles) + ".\n\n"
        prompt += "Goal: " + sanitize_field(goal, "goal") + "\n\n"
        prompt += "Respond with a JSON array where each element has keys: 'role' (one of " + str(available_roles) + "), 'goal' (sub-task description), 'constraints' (list of strings). Return ONLY the JSON array."

        last_error = None
        for attempt in range(1, self._LLM_DECOMPOSE_MAX_RETRIES + 1):
            try:
                raw = await asyncio.to_thread(self.llm.complete, prompt)
                # Extract JSON array from response (handle markdown fences)
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                tasks = json.loads(raw)
                if isinstance(tasks, list) and all(isinstance(t, dict) for t in tasks):
                    # Validate roles and field types — drop malformed entries
                    valid = []
                    for t in tasks:
                        if t.get("role") not in self.registry:
                            continue
                        if not isinstance(t.get("goal"), str) or not t["goal"]:
                            continue
                        if "constraints" not in t or not isinstance(t["constraints"], list):
                            t["constraints"] = []
                        valid.append(t)
                    if valid:
                        return valid[:self._max_concurrent_agents]
                logger.warning("LLM decomposition attempt %d returned no valid tasks", attempt)
            except Exception as e:
                last_error = e
                logger.warning("LLM decomposition attempt %d failed: %s", attempt, e)

        logger.warning("LLM decomposition exhausted %d retries (last error: %s), falling back to heuristic",
                        self._LLM_DECOMPOSE_MAX_RETRIES, last_error)
        return self._heuristic_decompose(goal)

    # Keyword-to-role mapping for heuristic decomposition.
    # Each entry: (keywords, tasks_template) where tasks_template is a list of
    # (role, goal_template, constraints) tuples.  "{goal}" is replaced with the
    # sanitised goal text.
    _HEURISTIC_RULES = [
        (
            {"audit", "verify", "validate", "check", "integrity"},
            [
                ("auditor", "Validate the structural integrity of the target entity.", ["check existence", "validate relationship"]),
                ("researcher", "Investigate semantic context and background information.", ["retrieve historical evidence"]),
            ],
        ),
        (
            {"research", "find", "search", "explore", "investigate", "discover"},
            [
                ("researcher", "Conduct deep dive into: {goal}", ["provide high-confidence evidence"]),
            ],
        ),
        (
            {"summarize", "describe", "explain", "overview", "report"},
            [
                ("researcher", "Gather relevant information for: {goal}", ["collect comprehensive evidence"]),
                ("auditor", "Verify accuracy of gathered information.", ["cross-reference sources"]),
            ],
        ),
        (
            {"compare", "contrast", "difference", "versus"},
            [
                ("researcher", "Research each subject in: {goal}", ["gather comparable data points"]),
                ("auditor", "Validate the comparison criteria and results.", ["ensure fair comparison"]),
            ],
        ),
    ]

    def _heuristic_decompose(self, goal: str) -> List[Dict[str, Any]]:
        """Keyword-based fallback for goal decomposition."""
        goal_lower = goal.lower()
        safe_goal = sanitize_field(goal, "goal")

        for keywords, template in self._HEURISTIC_RULES:
            if any(kw in goal_lower for kw in keywords):
                # Only emit tasks for roles that are actually registered
                tasks = []
                for role, goal_tmpl, constraints in template:
                    if role in self.registry:
                        tasks.append({
                            "role": role,
                            "goal": goal_tmpl.replace("{goal}", safe_goal),
                            "constraints": constraints,
                        })
                if tasks:
                    return tasks

        # Default: use every registered role with the original goal
        if len(self.registry) > 1:
            return [
                {"role": role, "goal": safe_goal, "constraints": []}
                for role in list(self.registry.keys())[:self._max_concurrent_agents]
            ]
        return [{"role": list(self.registry.keys())[0], "goal": safe_goal, "constraints": []}]

    async def run_goal(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        The main entry point for executing a complex goal.
        Manages the parallel execution and synthesis of agent results.
        """
        # Work on a copy so we don't mutate the caller's dict
        context = {**context, "refinements": self.refinement_registry.get_all()}
        
        tasks_data = await self.decompose_task(goal)
        
        # Convert task dicts into formal AgentTask objects
        tasks = [AgentTask(t["goal"], t["constraints"]) for t in tasks_data]
        
        logger.info("Dispatched %d sub-tasks.", len(tasks))
        
        # Prepare the agent coroutines for parallel execution
        semaphore = asyncio.Semaphore(self._max_concurrent_agents)
        agent_tasks = []
        local_agents = []

        for i, task in enumerate(tasks):
            role = tasks_data[i]["role"]
            if role in self.registry:
                # Instantiate the agent
                agent_id = f"{role}_{i:02d}"
                agent_instance = self.registry[role](agent_id, role, self.llm)
                local_agents.append(agent_instance)

                logger.info("Spawning %s (%s)...", agent_instance.agent_id, role)

                # Schedule the agent's run method with concurrency limit
                agent_tasks.append(self._execute_agent_bounded(semaphore, agent_instance, task, context))
            else:
                logger.warning("Unknown role: %s", role)

        # Snapshot local agents into the shared list for external visibility
        async with self._agents_lock:
            self.active_agents.extend(local_agents)

        # Execute all agents concurrently (bounded by semaphore)
        raw_results = await asyncio.gather(*agent_tasks)

        # Remove this invocation's completed/failed agents from the shared list
        finished = set(id(a) for a in local_agents)
        async with self._agents_lock:
            self.active_agents = [
                a for a in self.active_agents if id(a) not in finished
            ]

        # Synthesize findings
        final_report = self._synthesize(goal, raw_results)
        
        # --- NEW: Recursive Learning Step ---
        if self.ingestor:
            logger.info("Triggering Intelligence Ingestion for goal: '%s'", goal)
            # We pass the final_report and the context to the ingestor
            success = await self.ingestor.ingest(final_report, context)
            if success:
                logger.info("Learning successful: Findings ingested into Semantic Memory.")
            else:
                logger.warning("Learning failed: Ingestion unsuccessful.")
        # ------------------------------------

        # --- NEW: Autopoietic Tool Refinement Step ---
        refinement_proposals = [
            res.refinement_proposal for res in raw_results 
            if res.refinement_proposal is not None
        ]
        if refinement_proposals:
            logger.info("%d refinement proposals detected from agent findings.", len(refinement_proposals))
            await self._handle_refinement_proposals(refinement_proposals, context)
        # --------------------------------------------

        # --- Meta-Reflection: evaluate if the roster needs a new role ---
        await self._perform_meta_reflection(goal, final_report)
        # ---------------------------------------------------------------

        return final_report

    async def _execute_agent_bounded(self, semaphore: asyncio.Semaphore, agent: HermesAgent, task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        """Wraps _execute_agent with a concurrency semaphore."""
        async with semaphore:
            return await self._execute_agent(agent, task, context)

    async def _execute_agent(self, agent: HermesAgent, task: AgentTask, context: Dict[str, Any]) -> AgentResult:
        """Helper to run an agent and catch any lifecycle failures."""
        try:
            return await agent.run(task, context)
        except Exception as e:
            logger.error("Fatal error in agent %s: %s", agent.agent_id, e)
            return AgentResult(
                finding=f"Agent failure: {type(e).__name__}",
                confidence=0.0,
                evidence=[],
                status=AgentStatus.FAILED
            )

    def _synthesize(self, goal: str, results: List[AgentResult]) -> Dict[str, Any]:
        """
        Combines the findings from multiple agents into a single, coherent narrative.
        """
        logger.info("Synthesizing agent findings...")
        
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
            
            if res.status == AgentStatus.COMPLETED:
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

    async def _handle_refinement_proposals(self, proposals: List[Any], context: Dict[str, Any]) -> None:
        """
        Processes refinement proposals by using the LLM to validate them.
        In a full implementation, this would trigger a RefinementAgent.
        """
        if not self.llm:
            logger.warning("No LLM configured — cannot evaluate %d refinement proposal(s).", len(proposals))
            return

        for proposal in proposals:
            logger.info("Evaluating proposal: %s", proposal.rationale)

            prompt = "You are the Meta-Orchestrator Critic. Evaluate the following self-optimization proposal from an agent. Decide if the proposal is valid, safe, and would improve system performance.\n\n"
            prompt += "Proposal Type: " + sanitize_field(proposal.proposal_type, "proposal_type") + "\n"
            prompt += "Target: " + sanitize_field(proposal.target_component, "target") + "\n"
            prompt += "Current State: " + sanitize_field(proposal.current_state, "current_state") + "\n"
            prompt += "Proposed State: " + sanitize_field(proposal.proposed_state, "proposed_state") + "\n"
            prompt += "Rationale: " + sanitize_field(proposal.rationale, "rationale") + "\n\n"
            prompt += "Respond with JSON: {'approved': true/false, 'reasoning': '...'}"

            try:
                raw = await asyncio.to_thread(self.llm.complete, prompt)
                # Clean markdown if present
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                
                decision = json.loads(raw)
                if not isinstance(decision, dict):
                    logger.warning("LLM returned non-dict for refinement evaluation — skipping.")
                    continue
                approved = decision.get("approved")
                if approved is not True:
                    # Strict bool — "maybe", 1, "true" etc. all rejected
                    logger.info("Proposal REJECTED: %s", decision.get("reasoning"))
                    continue
                logger.info("Proposal APPROVED: %s", decision.get("reasoning"))
                self.refinement_registry.apply(proposal)
                logger.info("Applying evolution for %s...", proposal.target_component)
            except Exception as e:
                logger.warning("Failed to evaluate refinement proposal: %s", e)

    _META_REFLECTION_CONFIDENCE_THRESHOLD = 0.7

    # Only these role names may be bootstrapped via meta-reflection.
    # Prevents an adversarial LLM from registering arbitrary roles.
    ALLOWED_BOOTSTRAP_ROLES = frozenset({
        "analyst",
        "validator",
        "summarizer",
        "investigator",
        "fact_checker",
        "correlator",
    })

    async def _perform_meta_reflection(self, goal: str, report: Dict[str, Any]) -> None:
        """
        Analyzes the orchestration summary to decide if the current agent roster
        is sufficient or if a new agent role should be bootstrapped.

        Triggered after run_goal when aggregate confidence is low, suggesting
        the existing roles couldn't handle the goal well.
        """
        if not self.llm:
            return

        summary = report.get("orchestration_summary", {})
        confidence = summary.get("aggregate_confidence", 1.0)
        dispatched = summary.get("agents_dispatched", 0)

        if confidence >= self._META_REFLECTION_CONFIDENCE_THRESHOLD and dispatched >= 1:
            return

        logger.info("Meta-reflection: Low confidence (%.2f) with %d agent(s). Evaluating role evolution...",
                     confidence, dispatched)

        roles_list = list(self.registry.keys())
        prompt = (
            "You are the Meta-Orchestrator for a multi-agent system. The system just attempted "
            "a goal but produced low-confidence results, suggesting the current agent roster is insufficient.\n\n"
            f"Available agent roles: {roles_list}\n"
            f"Goal attempted: {sanitize_field(goal, 'goal')}\n"
            f"Outcome: {confidence * 100:.1f}% confidence with {dispatched} agent(s).\n\n"
            "Propose a single new specialized agent role that could better handle this type of task. "
            "Respond in JSON: {\"role_name\": \"...\", \"description\": \"...\"}\n"
            "If the existing roles are sufficient and the low confidence is expected, "
            "respond with: {\"role_name\": null, \"description\": \"No new role needed.\"}"
        )

        try:
            raw = await asyncio.to_thread(self.llm.complete, prompt)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            suggestion = json.loads(raw)
            if not isinstance(suggestion, dict):
                return

            role_name = suggestion.get("role_name")
            if not role_name or not isinstance(role_name, str):
                logger.info("Meta-reflection: LLM determined no new role is needed.")
                return

            # Sanitize role_name: enforce length and character constraints
            role_name = role_name.strip()[:64]
            if not role_name.replace("_", "").replace("-", "").isalnum():
                logger.warning("Meta-reflection: Invalid role name '%s' — must be alphanumeric/underscores.", role_name)
                return

            if role_name not in self.ALLOWED_BOOTSTRAP_ROLES:
                logger.warning("Meta-reflection: Role '%s' not in ALLOWED_BOOTSTRAP_ROLES — rejected.", role_name)
                return

            if role_name in self.registry:
                logger.info("Meta-reflection: Suggested role '%s' already exists.", role_name)
                return

            from domain.core.agents_impl import ResearcherAgent
            logger.warning(
                "Meta-reflection: Bootstrapping role '%s' with ResearcherAgent as base. "
                "This role will behave identically to 'researcher' until a specialized "
                "agent class is implemented.", role_name
            )
            self.register_agent_role(role_name, ResearcherAgent)
        except Exception as e:
            logger.warning("Meta-reflection failed: %s", e)
