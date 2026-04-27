import asyncio
import os
import sys
import datetime
import re

# Add the memory engine to sys.path
engine_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../repos/hermes-memory-engine"))
if engine_path not in sys.path:
    sys.path.append(engine_path)

src_path = os.path.join(engine_path, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from domain.core.decision_engine import ConflictMap, PathOption
    from application.decision_orchestrator import DecisionOrchestrator
    from application.engine import MemoryEngine
    from domain.core.graph_reasoning_engine import GraphReasoningEngine
    from application.evolution_orchestrator import EvolutionOrchestrator
    from domain.core.evolution import EvolutionEvent, EvolutionManifest, EvolutionType
    print("Successfully imported components for Proactive Agent.")
except ImportError as e:
    print(f"Error importing components: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

class ProactiveAgent:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.orchestrator = DecisionOrchestrator(workspace_root)
        self.engine = self.orchestrator.engine
        self.graph_reasoning = GraphReasoningEngine()
        self.evolution_orchestrator = EvolutionOrchestrator(workspace_root)
        
        self.tension_patterns = [
            r"(?i)tension between (.*) and (.*)",
            r"(?i)conflict between (.*) and (.*)",
            r"(?i)struggle to balance (.*) with (.*)",
            r"(?i)dilemma: (.*)",
            r"(?i)choice between (.*) vs (.*)"
        ]

    async def scan_for_tensions(self):
        print(f"[{datetime.datetime.now().isoformat()}] Proactive Scan: Initiating dual-layer tension detection...")
        
        # Layer 1: Semantic Log Scanning (Heuristic/Keyword)
        print("  -> [Layer 1] Scanning semantic logs for linguistic tension indicators...")
        recent_entries = self.engine.query("tension conflict dilemma choice balance")
        
        if recent_entries:
            print(f"  -> Found {len(recent_entries)} potential linguistic signals. Analyzing...")
            for entry in recent_entries:
                text = entry.get('text', '')
                found_pattern = False
                for pattern in self.tension_patterns:
                    match = re.search(pattern, text)
                    if match:
                        path_a_val = match.group(1).strip()
                        path_b_val = match.group(2).strip()
                        
                        print(f"  -> [SIGNAL] Linguistic tension: {path_a_val} vs {path_b_val}")
                        
                        conflict = ConflictMap(
                            tension_summary=f"Linguistic signal: {path_a_val} vs {path_b_val}",
                            paths=[
                                PathOption(id="A", description=f"Prioritize {path_a_val}", driving_value=path_a_val, primary_risk="High risk of neglecting secondary value"),
                                PathOption(id="B", description=f"Prioritize {path_b_val}", driving_value=path_b_val, primary_risk="High risk of neglecting secondary value")
                            ],
                            friction_point=f"Inherent tension identified via linguistic patterns: {path_a_val} vs {path_b_val}."
                        )
                        
                        print(f"  -> Triggering Decision Engine for linguistic conflict...")
                        result = await self.orchestrator.resolve_tension(conflict)
                        
                        # --- EVOLUTION HOOK ---
                        dm = None
                        if result:
                            if hasattr(result, 'decision_manifest'):
                                dm = result.decision_manifest
                            elif isinstance(result, dict):
                                dm = result.get('decision_manifest')
                            else:
                                dm = result

                        dm_trace = ""
                        if dm:
                            if hasattr(dm, 'reasoning_trace'):
                                dm_trace = dm.reasoning_trace
                            elif isinstance(dm, dict):
                                dm_trace = dm.get('reasoning_trace', '')

                        if dm_trace and "Axiomatic" in dm_trace:
                            print("  -> [EVOLUTION DETECTED] This resolution implies a new fundamental principle.")
                            evo_event = EvolutionEvent(
                                event_id=f"ev-lin-{datetime.datetime.now().timestamp()}",
                                evolution_type=EvolutionType.ESSENCE_SHIFT,
                                summary="Integrated Axiomatic Momentum: Integrating integrity as a geometric property of movement.",
                                evidence={"resolution": result.__dict__ if hasattr(result, '__dict__') else result},
                                impact_score=0.9
                            )
                            manifest = EvolutionManifest(
                                event=evo_event,
                                target_file="SOUL.md",
                                proposed_changes="Adopted the Axiomatic Momentum paradigm: Integrity is no longer a checkpoint, but the geometry of our movement.",
                                validation_criteria=["SOUL.md contains the new paradigm"]
                            )
                            await self.evolution_orchestrator.execute_evolution(manifest)
                        elif dm_trace and "Cryptographic" in dm_trace:
                            print("  -> [EVOLUTION DETECTED] This structural resolution implies a fundamental paradigm shift.")
                            evo_event = EvolutionEvent(
                                event_id=f"ev-str-{datetime.datetime.now().timestamp()}",
                                evolution_type=EvolutionType.ESSENCE_SHIFT,
                                summary="Integrated Cryptographic Sovereignty: Security redefined as mathematical agency.",
                                evidence={"resolution": result.__dict__ if hasattr(result, '__dict__') else result},
                                impact_score=0.95
                            )
                            manifest = EvolutionManifest(
                                event=evo_event,
                                target_file="SOUL.md",
                                proposed_changes="Adopted Cryptographic Sovereignty: Security is redefined as the mathematical guarantee of individual agency.",
                                validation_criteria=["SOUL.md contains the new paradigm"]
                            )
                            await self.evolution_orchestrator.execute_evolution(manifest)
                        elif result and (("Axiomatic" in str(result.decision)) or ("Axiomatic" in dm_trace)):
                            print("  -> [EVOLUTION DETECTED] This resolution implies a new fundamental principle.")
                            evo_event = EvolutionEvent(
                                event_id=f"ev-lin-{datetime.datetime.now().timestamp()}",
                                evolution_type=EvolutionType.ESSENCE_SHIFT,
                                summary="Integrated Axiomatic Momentum: Integrating integrity as a geometric property of movement.",
                                evidence={"resolution": result.__dict__ if hasattr(result, '__dict__') else result},
                                impact_score=0.9
                            )
                            manifest = EvolutionManifest(
                                event=evo_event,
                                target_file="SOUL.md",
                                proposed_changes="Adopted the Axiomatic Momentum paradigm: Integrity is no longer a checkpoint, but the geometry of our movement.",
                                validation_criteria=["SOUL.md contains the new paradigm"]
                            )
                            await self.evolution_orchestrator.execute_evolution(manifest)
                        elif result and (("Cryptographic" in str(result.decision)) or ("Cryptographic" in dm_trace)):
                            print("  -> [EVOLUTION DETECTED] This structural resolution implies a fundamental paradigm shift.")
                            evo_event = EvolutionEvent(
                                event_id=f"ev-str-{datetime.datetime.now().timestamp()}",
                                evolution_type=EvolutionType.ESSENCE_SHIFT,
                                summary="Integrated Cryptographic Sovereignty: Security redefined as mathematical agency.",
                                evidence={"resolution": result.__dict__ if hasattr(result, '__dict__') else result},
                                impact_score=0.95
                            )
                            manifest = EvolutionManifest(
                                event=evo_event,
                                target_file="SOUL.md",
                                proposed_changes="Adopted Cryptographic Sovereignty: Security is redefined as the mathematical guarantee of individual agency.",
                                validation_criteria=["SOUL.md contains the new paradigm"]
                            )
                            await self.evolution_orchestrator.execute_evolution(manifest)
                        elif result and (("Recursive Fractal Architecture" in str(result.decision)) or ("Recursive Fractal" in dm_trace)):
                            print("  -> [EVOLUTION DETECTED] This structural resolution implies a new topological principle.")
                            evo_event = EvolutionEvent(
                                event_id=f"ev-str-{datetime.datetime.now().timestamp()}",
                                evolution_type=EvolutionType.ESSENCE_SHIFT,
                                summary="Integrated Recursive Fractal Architecture: Expansion as structural reinforcement.",
                                evidence={"resolution": result.__dict__ if hasattr(result, '__dict__') else result},
                                impact_score=0.92
                            )
                            manifest = EvolutionManifest(
                                event=evo_event,
                                target_file="SOUL.md",
                                proposed_changes="Adopted the Recursive Fractal Architecture: Expansion is the mechanism of structural reinforcement.",
                                validation_criteria=["SOUL.md contains the new paradigm"]
                            )
                            await self.evolution_orchestrator.execute_evolution(manifest)

                        if result:
                            print(f"  -> [PROACTIVE SUCCESS] Tension resolved via Path C synthesis.")
                        else:
                            print(f"  -> [PROACTIVE FAILURE] Orchestrator could not resolve the detected tension.")
                        
                        found_pattern = True
                        break
                if found_pattern:
                    break

        # Layer 2: Structural Graph Scanning (Relational Intelligence)
        print("\n  -> [Layer 2] Scanning KnowledgeGraph for structural tension patterns...")
        
        try:
            kg = self.engine.graph_manager.graph
            structural_tensions = await self.graph_reasoning.detect_structural_tensions(kg)
            
            if structural_tensions:
                print(f"  -> Found {len(structural_tensions)} structural tension points.")
                for tension in structural_tensions:
                    print(f"  -> [STRUCTURAL SIGNAL] {tension.tension_type.upper()}: {tension.description} (Severity: {tension.severity})")
                    
                    if tension.tension_type == "contradiction":
                        conflict = ConflictMap(
                            tension_summary=f"Structural Contradiction: {tension.description}",
                            paths=[
                                PathOption(id="S", description="Synthesize a middle ground", driving_value="synthesis", primary_risk="Potential dilution of core values"),
                                PathOption(id="P", description="Prioritize primary node", driving_value="priority", primary_risk="Ignored opposing context")
                            ],
                            friction_point=tension.description
                        )
                        print(f"  -> Triggering Decision Engine for structural resolution...")
                        result = await self.orchestrator.resolve_tension(conflict)

                        # --- EVOLUTION HOOK ---
                        dm = None
                        if result:
                            if hasattr(result, 'decision_manifest'):
                                dm = result.decision_manifest
                            elif isinstance(result, dict):
                                dm = result.get('decision_manifest')
                            else:
                                dm = result

                        dm_trace = ""
                        if dm:
                            if hasattr(dm, 'reasoning_trace'):
                                dm_trace = dm.reasoning_trace
                            elif isinstance(dm, dict):
                                dm_trace = dm.get('reasoning_trace', '')

                        if dm_trace and "Axiomatic" in dm_trace:
                            print("  -> [EVOLUTION DETECTED] This resolution implies a new fundamental principle.")
                            evo_event = EvolutionEvent(
                                event_id=f"ev-lin-{datetime.datetime.now().timestamp()}",
                                evolution_type=EvolutionType.ESSENCE_SHIFT,
                                summary="Integrated Axiomatic Momentum: Integrating integrity as a geometric property of movement.",
                                evidence={"resolution": result.__dict__ if hasattr(result, '__dict__') else result},
                                impact_score=0.9
                            )
                            manifest = EvolutionManifest(
                                event=evo_event,
                                target_file="SOUL.md",
                                proposed_changes="Adopted the Axiomatic Momentum paradigm: Integrity is no longer a checkpoint, but the geometry of our movement.",
                                validation_criteria=["SOUL.md contains the new paradigm"]
                            )
                            await self.evolution_orchestrator.execute_evolution(manifest)
                        elif dm_trace and "Cryptographic" in dm_trace:
                            print("  -> [EVOLUTION DETECTED] This structural resolution implies a fundamental paradigm shift.")
                            evo_event = EvolutionEvent(
                                event_id=f"ev-str-{datetime.datetime.now().timestamp()}",
                                evolution_type=EvolutionType.ESSENCE_SHIFT,
                                summary="Integrated Cryptographic Sovereignty: Security redefined as mathematical agency.",
                                evidence={"resolution": result.__dict__ if hasattr(result, '__dict__') else result},
                                impact_score=0.95
                            )
                            manifest = EvolutionManifest(
                                event=evo_event,
                                target_file="SOUL.md",
                                proposed_changes="Adopted Cryptographic Sovereignty: Security is redefined as the mathematical guarantee of individual agency.",
                                validation_criteria=["SOUL.md contains the new paradigm"]
                            )
                            await self.evolution_orchestrator.execute_evolution(manifest)
                        elif result and (("Axiomatic" in str(result.decision)) or ("Axiomatic" in dm_trace)):
                            print("  -> [EVOLUTION DETECTED] This resolution implies a new fundamental principle.")
                            evo_event = EvolutionEvent(
                                event_id=f"ev-lin-{datetime.datetime.now().timestamp()}",
                                evolution_type=EvolutionType.ESSENCE_SHIFT,
                                summary="Integrated Axiomatic Momentum: Integrating integrity as a geometric property of movement.",
                                evidence={"resolution": result.__dict__ if hasattr(result, '__dict__') else result},
                                impact_score=0.9
                            )
                            manifest = EvolutionManifest(
                                event=evo_event,
                                target_file="SOUL.md",
                                proposed_changes="Adopted the Axiomatic Momentum paradigm: Integrity is no longer a checkpoint, but the geometry of our movement.",
                                validation_criteria=["SOUL.md contains the new paradigm"]
                            )
                            await self.evolution_orchestrator.execute_evolution(manifest)
                        elif result and (("Cryptographic" in str(result.decision)) or ("Cryptographic" in dm_trace)):
                            print("  -> [EVOLUTION DETECTED] This structural resolution implies a fundamental paradigm shift.")
                            evo_event = EvolutionEvent(
                                event_id=f"ev-str-{datetime.datetime.now().timestamp()}",
                                evolution_type=EvolutionType.ESSENCE_SHIFT,
                                summary="Integrated Cryptographic Sovereignty: Security redefined as mathematical agency.",
                                evidence={"resolution": result.__dict__ if hasattr(result, '__dict__') else result},
                                impact_score=0.95
                            )
                            manifest = EvolutionManifest(
                                event=evo_event,
                                target_file="SOUL.md",
                                proposed_changes="Adopted Cryptographic Sovereignty: Security is redefined as the mathematical guarantee of individual agency.",
                                validation_criteria=["SOUL.md contains the new paradigm"]
                            )
                            await self.evolution_orchestrator.execute_evolution(manifest)
                        elif result and (("Recursive Fractal Architecture" in str(result.decision)) or ("Recursive Fractal" in dm_trace)):
                            print("  -> [EVOLUTION DETECTED] This structural resolution implies a new topological principle.")
                            evo_event = EvolutionEvent(
                                event_id=f"ev-str-{datetime.datetime.now().timestamp()}",
                                evolution_type=EvolutionType.ESSENCE_SHIFT,
                                summary="Integrated Recursive Fractal Architecture: Expansion as structural reinforcement.",
                                evidence={"resolution": result.__dict__ if hasattr(result, '__dict__') else result},
                                impact_score=0.92
                            )
                            manifest = EvolutionManifest(
                                event=evo_event,
                                target_file="SOUL.md",
                                proposed_changes="Adopted the Recursive Fractal Architecture: Expansion is the mechanism of structural reinforcement.",
                                validation_criteria=["SOUL.md contains the new paradigm"]
                            )
                            await self.evolution_orchestrator.execute_evolution(manifest)

                        if result:
                            print(f"  -> [PROACTIVE SUCCESS] Tension resolved via Path C synthesis.")
                        else:
                            print(f"  -> [PROACTIVE FAILURE] Orchestrator could not resolve the detected tension.")
                        
                        break
            else:
                print("  -> No structural tensions detected. Topology is stable.")
        except Exception as e:
            print(f"  -> [ERROR] Structural scan failed: {e}")

        print(f"\n[{datetime.datetime.now().isoformat()}] Proactive Scan Complete.")

async def main():
    workspace = "/opt/data/webui_data/workspace"
    agent = ProactiveAgent(workspace)
    await agent.scan_for_tensions()

if __name__ == "__main__":
    asyncio.run(main())
