import os
import sys
import asyncio
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
    print("Successfully imported components for Proactive Agent.")
except ImportError as e:
    print(f"Error importing components: {e}")
    sys.exit(1)

class ProactiveAgent:
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        self.orchestrator = DecisionOrchestrator(workspace_root)
        self.engine = self.orchestrator.engine
        
        self.tension_patterns = [
            r"(?i)tension between (.*) and (.*)",
            r"(?i)conflict between (.*) and (.*)",
            r"(?i)struggle to balance (.*) with (.*)",
            r"(?i)dilemma: (.*)",
            r"(?i)choice between (.*) vs (.*)"
        ]

    async def scan_for_tensions(self):
        print(f"[{datetime.datetime.now().isoformat()}] Proactive Scan: Searching logs for tension indicators...")
        
        recent_entries = self.engine.query("tension conflict dilemma choice balance")
        
        if not recent_entries:
            print("  -> No recent tension indicators found. System is in equilibrium.")
            return

        print(f"  -> Found {len(recent_entries)} potential tension signals. Analyzing...")

        for entry in recent_entries:
            text = entry.get('text', '')
            
            for pattern in self.tension_patterns:
                match = re.search(pattern, text)
                if match:
                    path_a_val = match.group(1).strip()
                    path_b_val = match.group(2).strip()
                    
                    print(f"  -> [SIGNAL DETECTED] Potential tension: {path_a_val} vs {path_b_val}")
                    
                    conflict = ConflictMap(
                        tension_summary=f"Proactively detected: {path_a_val} vs {path_b_val}",
                        paths=[
                            PathOption(id="A", description=f"Prioritize {path_a_val}", driving_value=path_a_val, primary_risk="High risk of neglecting secondary value"),
                            PathOption(id="B", description=f"Prioritize {path_b_val}", driving_value=path_b_val, primary_risk="High risk of neglecting secondary value")
                        ],
                        friction_point=f"The inherent tension between {path_a_val} and {path_b_val} identified in recent interaction logs."
                    )
                    
                    print(f"  -> Triggering Decision Engine for resolution...")
                    result = await self.orchestrator.resolve_tension(conflict)
                    
                    if result:
                        print(f"  -> [PROACTIVE SUCCESS] Tension resolved via Path C synthesis.")
                    else:
                        print(f"  -> [PROACTIVE FAILURE] Orchestrator could not resolve the detected tension.")
                    
                    break
            else:
                continue
            break

async def main():
    workspace = "/opt/data/webui_data/workspace"
    agent = ProactiveAgent(workspace)
    await agent.scan_for_tensions()

if __name__ == "__main__":
    asyncio.run(main())
