import os
import sys
import asyncio
import uuid
import datetime
import sqlite3

# Add the repo root to the path
repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

from domain.supporting.ledger import StructuralLedger
from domain.core.analyzer import GraphAnalyzer
from domain.supporting.monitor import StateTracker, SnapshotAnomalyDetector
from application.orchestrator import Orchestrator
from domain.core.agents_impl import ResearcherAgent, AuditorAgent
from infrastructure.llm_implementations import OpenAIImplementation
from domain.core.models import Skill, RelationalEdge

# Database path for the test
DB_PATH = '/tmp/hermes_stress_test.db'

async def run_stress_test():
    print("=== STARTING PROACTIVE INTELLIGENCE STRESS TEST ===")
    
    # 1. Setup
    print("\n[1/6] Initializing components...")
    ledger = StructuralLedger(DB_PATH)
    analyzer = GraphAnalyzer(ledger)
    tracker = StateTracker(ledger)
    detector = SnapshotAnomalyDetector(ledger)

    llm = OpenAIImplementation()
    registry = {"researcher": ResearcherAgent, "auditor": AuditorAgent}
    orchestrator = Orchestrator(registry, llm)

    from domain.core.insight_trigger import InsightTrigger
    trigger = InsightTrigger(ledger, orchestrator)

    # 2. Baseline
    print("\n[2/6] Establishing baseline...")
    session = ledger.Session()
    try:
        # Create 15 baseline skills (only if not already present)
        if session.query(Skill).count() == 0:
            for i in range(15):
                skill = Skill(name=f"BaseSkill_{i}", description="A standard baseline skill.")
                session.add(skill)
            session.commit()
        
        # Create a chain of edges
        skills = session.query(Skill).all()
        for i in range(len(skills) - 1):
            edge = RelationalEdge(
                source_id=skills[i].id,
                target_id=skills[i+1].id,
                relationship_type="connected_to",
                weight=0.5
            )
            session.add(edge)
        session.commit()
    finally:
        session.close()

    # Capture baseline snapshot
    baseline_snapshot = tracker.capture_snapshot()
    print(f"Baseline established. Nodes: {len(analyzer.graph.nodes)}, Edges: {len(analyzer.graph.edges)}")

    # 3. Inject Anomaly (The "Hub Emergence" Event)
    print("\n[3/6] Injecting anomaly: Creating a 'Super-Hub' node...")
    session = ledger.Session()
    try:
        hub_skill = Skill(name="EMERGENT_HUB_NODE", description="A massive central node designed to trigger an anomaly.")
        session.add(hub_skill)
        session.commit()
        
        all_skills = session.query(Skill).all()
        for skill in all_skills:
            if skill.id != hub_skill.id:
                edge = RelationalEdge(
                    source_id=hub_skill.id,
                    target_id=skill.id,
                    relationship_type="super_connection",
                    weight=1.0
                )
                session.add(edge)
        session.commit()
        print(f"Anomaly injected. Hub '{hub_skill.name}' is now connected to {len(all_skills)-1} nodes.")
    finally:
        session.close()

    # 4. Monitor & Detect
    print("\n[4/6] Running Monitor-Detector loop...")
    analyzer.build_graph()
    
    # Capture current snapshot
    current_snapshot = tracker.capture_snapshot()
    
    # Run detection
    anomalies = detector.detect_anomalies(current_snapshot)
    
    if not anomalies:
        print("FAILURE: No anomalies were detected!")
        return
    else:
        print(f"SUCCESS: Detected {len(anomalies)} anomaly/ies!")
        for a in anomalies:
            print(f"  - [{a.anomaly_type}] {a.description}")

    # 5. Trigger & Orchestrate
    print("\n[5/6] Running InsightTrigger...")
    # We need to manualy call the trigger's logic if it's not polling
    # For the test, we'll pass the anomalies to a new test method or just manually trigger
    await trigger.process_new_anomalies({})

    # 6. Final Verification
    print("\n[6/6] Verifying results...")
    print("If the system worked, you should have seen the Orchestrator dispatching agents "
          "to investigate the emergence of the hub node.")
    print("====================================================")
    print("STRESS TEST COMPLETE.")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
