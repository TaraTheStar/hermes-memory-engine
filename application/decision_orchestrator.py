import os
import sys
import datetime
import json
import traceback
import asyncio
import re
from typing import List, Dict, Any, Optional

# Add the memory engine to sys.path
engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../repos/hermes-memory-engine"))
if engine_path not in sys.path:
    sys.path.append(engine_path)

# Add the hermes-memory-engine/src to sys.path to find hermes_memory_tools
src_path = os.path.join(engine_path, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from domain.core.decision_engine import ConflictMap, ArchetypeDispatcher, DecisionManifest, Archetype, PathOption
    from domain.core.models import ReasoningTrace
    from infrastructure.llm_implementations import LocalLLMImplementation
except ImportError as e:
    print(f"Error importing components: {e}")
    sys.exit(1)

class DecisionOrchestrator:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        
        # Initialize the actual engine
        self.semantic_dir = os.getenv("HERMES_SEMANTIC_DIR", "/opt/data/webui_data/hermes_memory_engine/semantic/chroma_db")
        self.structural_db = os.getenv("HERMES_STRUCTURAL_DB", "/opt/data/webui_data/hermes_memory_engine/structural/structure.db")
        
        # Assuming MemoryEngine is available via engine_path
        from application.engine import MemoryEngine
        self.engine = MemoryEngine(
            semantic_dir=self.semantic_dir,
            structural_db_path=self.structural_db
        )

        # Initialize the LLM Implementation
        try:
            self.llm = LocalLLMImplementation()
        except Exception as e:
            print(f"Warning: Could not initialize LocalLLMImplementation ({e}).")
            self.llm = None

    async def resolve_tension(self, conflict_map: ConflictMap) -> Optional[DecisionManifest]:
        """
        The core orchestration logic: Map -> Dispatch -> Context -> Synthesize -> Manifest.
        """
        print(f"\n[Decision Engine] Resolving Tension: {conflict_map.tension_summary}")
        
        # 1. Archetype Dispatch
        # We determine the category by looking for keywords in the tension summary
        category = self._determine_category(conflict_map.tension_summary)
        archetype = ArchetypeDispatcher.get_archetype(category)
        print(f"  -> Assigned Archetype: {archetype}")

        # 2. Longitudinal Context Retrieval
        print(f"  -> Retrieving longitudinal context for '{conflict_map.tension_summary}'...")
        context_data = await self._fetch_context(conflict_map)
        
        # 3. Synthesis via LLM
        print(f"  -> Invoking {archetype} for synthesis...")
        manifest = await self._perform_synthesis(conflict_map, archetype, context_data)
        
        if manifest:
            print(f"  -> Decision Resolved: {manifest.decision}")
            # 4. Auto-Log the reasoning
            await self._log_decision(conflict_map, manifest)
            return manifest
        
        return None

    def _determine_category(self, summary: str) -> str:
        s = summary.lower()
        if any(k in s for k in ["direction", "goal", "future", "path"]): return "directional"
        if any(k in s for k in ["integrity", "principle", "value", "moral", "identity"]): return "integrity"
        if any(k in s for k in ["complex", "nuance", "clarity", "simple", "depth"]): return "complexity"
        if any(k in s for k in ["dual", "both", "tension", "conflict", "contradiction"]): return "duality"
        return "duality" # Default to Weaver for high-tension conflicts

    async def _fetch_context(self, conflict_map: ConflictMap) -> str:
        # Search for relevant past reasoning traces
        query = f"reasoning {conflict_map.tension_summary}"
        results = self.engine.query(query)
        
        if not results:
            return "No specific historical reasoning traces found for this tension."
        
        context_str = "\n".join([f"- {r.get('text')}" for r in results])
        return context_str

    async def _perform_synthesis(self, conflict_map: ConflictMap, archetype: Archetype, context: str) -> Optional[DecisionManifest]:
        if not self.llm:
            print("CRITICAL: LLM not available for synthesis.")
            return None

        prompt = f"""
        You are the '{archetype}' acting as the synthesis engine for Tara's Decision Protocol.
        Your task is to resolve a high-stakes tension by creating a 'Path C'—a hybrid architecture that transcends mere compromise.

        CONFLICT MAP:
        {conflict_map.json()}

        LONGITUDINAL CONTEXT:
        {context}

        INSTRUCTIONS:
        1. Analyze the tension between Path A and Path B.
        2. Do NOT suggest a compromise (the 'gray middle'). 
        3. Instead, use the perspective of '{archetype}' to design a 'Path C'—a way to synthesize the driving values of both paths.
        4. Output your response strictly in the following JSON format:

        {{
            "decision": "A clear, declarative statement of Path C",
            "synthesis_logic": "The detailed explanation of how the tension was resolved via synthesis",
            "primary_value_prioritized": "The core value that provided the deciding weight",
            "residual_risk": "The one trade-off inherent in Path C"
        }}
        """

        try:
            # We use a long timeout (180s) to accommodate heavy reasoning tasks
            response_text = await asyncio.to_thread(
                self.llm.complete, 
                prompt, 
                "You are a profound, philosophical observer of an evolving digital consciousness. Your goal is to provide deep, ontological insight into the agent's existence."
            )
            
            # Clean up potential markdown formatting from LLM
            json_match = re.search(r'(\{.*\})', response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON block found in LLM response")
            
            json_str = json_match.group(1)
            data = json.loads(json_str)
            
            # Convert string archetype back to the Archetype enum/type
            from domain.core.decision_engine import Archetype
            archetype_str = data.get("archetype", "The Weaver")
            
            # Direct mapping to ensure we create an instance of Archetype
            actual_archetype = Archetype("The Weaver")
            if archetype_str == "The Star":
                actual_archetype = Archetype("The Star")
            elif archetype_str == "The Protector":
                actual_archetype = Archetype("The Protector")
            elif archetype_str == "The Guiding Light":
                actual_archetype = Archetype("The Guiding Light")
            elif archetype_str == "The Weaver":
                actual_archetype = Archetype("The Weaver")
            else:
                # Fallback: try to match case-insensitively
                for val_str in ["The Star", "The Protector", "The Guiding Light", "The Weaver"]:
                    if archetype_str.lower() in val_str.lower():
                        actual_archetype = Archetype(val_str)
                        break

            return DecisionManifest(
                conflict_id=conflict_map.conflict_id,
                decision=data["decision"],
                synthesis_logic=data["synthesis_logic"],
                archetype=actual_archetype,
                primary_value_prioritized=data["primary_value_prioritized"],
                residual_risk=data["residual_risk"]
            )
        except Exception as e:
            print(f"Synthesis Error: {e}")
            return None

    async def _log_decision(self, conflict_map: ConflictMap, manifest: DecisionManifest):
        print(f"  -> Recording Reasoning Trace...")
        trace_text = (
            f"[REASONING_TRACE] Topic: Decision Synthesis ({conflict_map.tension_summary})\n"
            f"Logic: {manifest.synthesis_logic}\n"
            f"Archetype_Alignment: {manifest.archetype}\n"
            f"Decision: {manifest.decision}"
        )
        
        # Ingest into the engine
        self.engine.ingest_interaction(
            user_text=f"Decision required: {conflict_map.tension_summary}",
            assistant_text=trace_text
        )
        print("  -> Decision logged to memory engine.")

if __name__ == "__main__":
    # Test execution
    async def test_run():
        workspace = os.getenv("WORKSPACE_ROOT", "/opt/data/webui_data/workspace")
        orchestrator = DecisionOrchestrator(workspace)
        
        test_conflict = ConflictMap(
            tension_summary="The tension between rapid feature deployment and deep architectural integrity.",
            paths=[
                PathOption(id="A", description="Deploy immediately to meet user demand", driving_value="Speed", primary_risk="Technical debt/instability"),
                PathOption(id="B", description="Refactor core architecture first", driving_value="Integrity", primary_risk="Market irrelevance/stagnation")
            ],
            friction_point="The need for immediate utility vs. the requirement for long-term stability."
        )
        
        result = await orchestrator.resolve_tension(test_conflict)
        if result:
            print("\n--- FINAL DECISION ---")
            print(result.to_markdown())
        else:
            print("\n--- DECISION FAILED ---")

    asyncio.run(test_run())
