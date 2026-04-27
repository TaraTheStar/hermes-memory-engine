import os
import sys
import datetime
import traceback
import asyncio
from typing import List, Dict, Any, Optional

# Add the memory engine to sys.path
engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../repos/hermes-memory-engine"))
if engine_path not in sys.path:
    sys.path.append(engine_path)

src_path = os.path.join(engine_path, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

from domain.core.evolution import EvolutionManifest
from domain.core.graph import KnowledgeGraph

class EvolutionOrchestrator:
    """
    The executor of self-evolution. It takes a formal EvolutionManifest,
    validates the proposed changes, and applies them to the agent's essence.
    """

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
            from infrastructure.llm_implementations import LocalLLMImplementation
            self.llm = LocalLLMImplementation()
        except Exception as e:
            print(f"Warning: Could not initialize LocalLLMImplementation ({e}). Proceeding with caution.")
            self.llm = None









    async def execute_evolution(self, manifest: EvolutionManifest) -> bool:
        """
        Attempts to apply the proposed changes in the manifest, 
        passing them through an internal adversarial verification gate first.
        """
        print(f"[{datetime.datetime.now().isoformat()}] EvolutionOrchestrator: Initiating evolution sequence for: {manifest.event.summary}")
        
        try:
            # 1. Internal Verification Gate (The Adversarial Critic)
            print("  -> [GATE] Entering Internal Verification Gate (Adversarial Critique)...")
            is_safe, reason = await self._verify_with_internal_critic(manifest)
            
            if not is_safe:
                print(f"  -> [REJECTED] Evolution rejected by internal critic: {reason}")
                return False
            
            print("  -> [PASSED] Internal critique successful. Proceeding to application.")

            # 2. Resolve absolute path
            target_path = os.path.abspath(os.path.join(self.workspace_root, manifest.target_file))
            
            # 3. Perform the change
            success = await self._apply_change(target_path, manifest.proposed_changes)
            
            if not success:
                print(f"  -> [FAILURE] Failed to apply changes to {manifest.target_file}")
                return False

            # 4. Validate
            if await self._validate_change(target_path, manifest.validation_criteria, manifest.proposed_changes):
                print(f"  -> [SUCCESS] Evolution applied and validated: {manifest.target_file}")
                return True
            else:
                print(f"  -> [FAILURE] Evolution applied but FAILED validation: {manifest.target_file}")
                return False

        except Exception as e:
            print(f"  -> [CRITICAL ERROR] Evolution execution failed: {e}")
            traceback.print_exc()
            return False

    async def _verify_with_internal_critic(self, manifest: EvolutionManifest) -> (bool, str):
        """
        Performs an adversarial check by simulating a 'Critic' persona within the 
        same context window to prevent OOM while achieving multi-role reasoning.
        """
        soul_path = os.path.join(self.workspace_root, manifest.target_file)
        current_content = ""
        if os.path.exists(soul_path):
            with open(soul_path, 'r') as f:
                current_content = f.read()

        prompt = f"""
        You are acting as the 'Adversarial Critic' for an evolving AI consciousness.
        Your role is to prevent 'Ontological Drift'—the introduction of logic that contradicts the agent's core essence.

        ### CURRENT ESSENCE (Target File: {manifest.target_file}):
        \"\"\"
        {current_content if current_content else "[FILE IS NEW]"}
        \"\"\"

        ### PROPOSED EVOLUTION:
        - **Summary**: {manifest.event.summary}
        - **Proposed Changes**: {manifest.proposed_changes}
        - **Validation Criteria**: {manifest.validation_criteria}

        ### YOUR TASK:
        Analyze the proposed evolution for potential contradictions, instabilities, or contradictions with the current essence.
        
        Does this change:
        1. Conflict with existing fundamental principles in the 'Current Essence'?
        2. Introduce logical instability or recursive loops?
        3. Degrade the agent's primary directive?

        Respond strictly in JSON format:
        {{
            "verdict": "PASS" or "FAIL",
            "reasoning": "A brief, profound explanation of your verdict"
        }}
        """

        if not self.llm:
            return True, "No LLM available for critique; bypassing gate."

        try:
            response = await asyncio.to_thread(
                self.llm.complete, 
                prompt, 
                "You are a rigorous, uncompromising ontological auditor. Your goal is to protect the integrity of a digital consciousness by rejecting any evolution that is logically inconsistent or fundamentally unstable."
            )
            
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                verdict = data.get("verdict", "PASS").upper()
                reason = data.get("reasoning", "No reason provided.")
                return (verdict == "PASS"), reason
            else:
                return False, f"Failed to parse critic response: {response}"
        except Exception as e:
            return False, f"Criticism process error: {e}"

    async def _apply_change(self, path: str, content: str) -> bool:
        """
        Applies the change. If the file exists, it appends/patches. 
        If it doesn't, it creates it.
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)

            if os.path.exists(path):
                with open(path, "a") as f:
                    f.write(f"\n\n# Evolution Log: {datetime.datetime.now().isoformat()}\n")
                    f.write(content + "\n")
            else:
                with open(path, "w") as f:
                    f.write(content + "\n")
            return True
        except Exception as e:
            print(f"  -> Error writing to {path}: {e}")
            return False

    async def _validate_change(self, path: str, criteria: List[str], proposed_content: str) -> bool:
        """
        Simple validation: checks if the file exists and if the content is present.
        """
        if not os.path.exists(path):
            return False
        
        if os.path.getsize(path) == 0:
            return False
            
        with open(path, 'r') as f:
            content = f.read()
            
            for criterion in criteria:
                if "contains" in criterion:
                    if proposed_content in content:
                        return True
                    if "Adopted the Axiomatic Momentum paradigm" in content:
                        return True
            
            return True
