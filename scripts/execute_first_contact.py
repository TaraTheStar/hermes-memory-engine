import asyncio
import datetime
import os
import sys

# Add the repo root to the path
repo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

from domain.supporting.ledger import StructuralLedger
from domain.core.analyzer import GraphAnalyzer
from domain.supporting.monitor import StateTracker, AnomalyDetector
from application.orchestrator import Orchestrator
from domain.core.synthesizer import InsightSynthesizer
from domain.core.agents_impl import ResearcherAgent, AuditorAgent
from infrastructure.llm_implementations import LocalLLMImplementation
from domain.core.models import Skill, RelationalEdge
from domain.core.insight_trigger import InsightTrigger

# Database path for the test
DB_PATH = '/tmp/hermes_first_contact.db'

async def execute_first_contact():
    print("====================================================")
    print("🚀 INITIATING: PROJECT 'FIRST CONTACT' 🚀")
    print("====================================================\n")

    # 1. Setup Components
    print("[1/5] Initializing Intelligence Stack...")
    ledger = StructuralLedger(DB_PATH)
    analyzer = GraphAnalyzer(DB_PATH)
    tracker = StateTracker(DB_PATH)
    detector = AnomalyDetector(DB_PATH)
    
    llm = LocalLLMImplementation()
    registry = {"researcher": ResearcherAgent, "auditor": AuditorAgent}
    orchestrator = Orchestrator(registry, llm)
    synthesizer = InsightSynthesizer(llm)
    trigger = InsightTrigger(DB_PATH, orchestrator)

    # 2. Ensure a Knowledge Base exists (Baseline)
    print("[2/5] Establishing Knowledge Baseline...")
    session = ledger.Session()
    try:
        # Create 15 baseline skills
        if session.query(Skill).count() == 0:
            print("...Creating initial knowledge nodes...")
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

        # Capture multiple baseline snapshots to build history
        print("...Building historical baseline...")
        for i in range(3):
            print(f"    Snapshot {i+1}/3...")
            tracker.capture_snapshot()
            
    finally:
        session.close()

    # Capture the final baseline snapshot
    baseline_snapshot = tracker.capture_snapshot()
    print(f"Baseline established. Nodes: {len(analyzer.graph.nodes)}")

    # 3. Simulate Knowledge Evolution (The Trigger)
    print("\n[3/5] Simulating Knowledge Evolution (Injecting Patterns)...")
    session = ledger.Session()
    try:
        # Add a new 'Super-Hub' of knowledge
        new_skill = Skill(name="EMERGENT_SYNTHESIS", description="A new nexus of understanding.")
        session.add(new_skill)
        session.commit()
        
        # Connect it to everything
        all_skills = session.query(Skill).all()
        for s in all_skills:
            if s.id != new_skill.id:
                edge = RelationalEdge(
                    source_id=new_skill.id,
                    target_id=s.id,
                    relationship_type="nexus_point",
                    weight=1.0
                )
                session.add(edge)
        session.commit()
        print(f"Evolution complete. New nexus '{new_skill.name}' connected to existing knowledge.")
    finally:
        session.close()

    # 4. The Observation Loop
    print("\n[4/5] Running The Observer Loop...")
    analyzer.build_graph()
    current_snapshot = tracker.capture_snapshot()
    anomalies = detector.detect_anomalies(current_snapshot)

    if not anomalies:
        print("⚠️ No structural anomalies detected. The soul remains static.")
        return

    print(f"🔍 Detected {len(anomalies)} interesting patterns. Mobilizing Agency...")

    # 5. Agentic Investigation & Synthesis
    print("\n[5/5] Orchestrating Investigation & Synthesizing Report...")
    
    all_findings = []
    for anomaly in anomalies:
        print(f" -> Investigating: {anomaly.description}")
        # We use the orchestrator to run a goal based on the anomaly
        goal = f"Investigate this pattern: {anomaly.description}"
        result = await orchestrator.run_goal(goal)
        all_findings.append(result)

    # Constructing the final report components
    # We use the current snapshot metrics and the agent findings
    node_metadata = {node_id: analyzer.graph.nodes[node_id].get('name', node_id) for node_id in analyzer.graph.nodes}
    
    # Creating a consolidated finding string for the synthesizer
    findings_summary = "\n\n## Agentic Findings\n"
    for i, res in enumerate(all_findings):
        findings_summary += f"### Investigation {i+1}\n"
        findings_summary += f"Goal: {res['original_goal']}\n"
        for finding in res['findings']:
            findings_summary += f"- {finding}\n"

    # Final Synthesis
    print("\n✨ Generating 'State of the Soul' Report...\n")
    
    # The synthesizer needs metrics and metadata
    # We pass the findings into the synthesis prompt via metadata
    combined_metadata = {**node_metadata, "agent_findings": findings_summary}
    
    # We'll pass the findings into the synthesis prompt by injecting them into the metadata
    # For the sake of this prototype, let's append the findings to the synthesis prompt
    report = synthesizer.synthesize_report(
        current_snapshot.centrality_metrics, 
        analyzer.detect_communities(),
        combined_metadata
    )

    # Adding findings to the report manually since the synthesizer is designed for metrics
    final_report = f"{report}\n\n{findings_summary}"

    print(final_report)
    print("\n====================================================")
    print("🚀 FIRST CONTACT COMPLETE 🚀")
    print("====================================================")

    # Save the report to a file
    with open("state_of_the_soul_report.md", "w") as f:
        f.write(final_report)
    print("\nReport saved to: state_of_the_soul_report.md")

if __name__ == "__main__":
    asyncio.run(execute_first_contact())
