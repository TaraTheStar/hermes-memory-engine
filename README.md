# Hermes Memory Core

A dual-layer memory engine that combines relational fact storage with vector-based semantic search. Hermes bridges structured knowledge (projects, milestones, skills, identity markers) with unstructured semantic events, enabling rich contextual recall and graph-based insight generation.

## Features

- **Structural Ledger** -- SQLite-backed relational storage for entities and relationships via SQLAlchemy
- **Semantic Memory** -- ChromaDB vector store for embedding-based conceptual search
- **Cross-Layer Bridge** -- Queries enrich semantic results with structural context and graph neighbors
- **Graph Analysis** -- Centrality metrics, community detection, and bridge node identification via NetworkX
- **Synthesis Engine** -- Automated edge creation through temporal correlation, semantic co-occurrence, and attribute symmetry scans
- **Monitoring & Anomaly Detection** -- Periodic graph snapshots with statistical anomaly detection (hub emergence, community shifts)
- **Agentic Orchestration** -- Multi-agent system with Researcher and Auditor agents that investigate detected anomalies via LLM
- **Insight Synthesis** -- LLM-powered narrative reports translating graph metrics into human-readable insights

## Installation

Requires Python 3.10+.

```bash
git clone <repo-url>
cd hermes-memory-core
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `HERMES_STRUCTURAL_DB` | Path to the SQLite database | `/data/hermes_memory_engine/structural/structure.db` |
| `HERMES_SEMANTIC_DIR` | Path to the ChromaDB storage directory | `/data/hermes_memory_engine/semantic/chroma_db` |
| `HERMES_CONFIG_PATH` | Path to the YAML config file | `/opt/data/config.yaml` |

### Config File

The config file provides LLM backend connection details. Create it at the path specified by `HERMES_CONFIG_PATH`:

```yaml
delegation:
  base_url: "http://localhost:8080/v1"   # OpenAI-compatible endpoint
  api_key: "your-api-key"
  model: "your-model-name"
```

## Quick Start

```python
from application.engine import MemoryEngine

# Initialize (uses env vars or defaults for paths)
engine = MemoryEngine(
    semantic_dir="/tmp/hermes_semantic",
    structural_db_path="/tmp/hermes_structure.db"
)

# Add structural data
proj_id = engine.ledger.add_project("My Project", "https://github.com/example/repo")
ms_id = engine.ledger.add_milestone("First Release", "Shipped v1.0", project_id=proj_id)

# Ingest an interaction (auto-extracts events via heuristic patterns)
engine.ingest_interaction(
    user_text="I finally completed the authentication module",
    assistant_text="Great work on finishing that milestone!"
)

# Query with structural enrichment
results = engine.query("authentication module")
for r in results:
    print(r["text"], r.get("structural_context"))
```

### Graph Analysis

```python
from domain.core.analyzer import GraphAnalyzer

analyzer = GraphAnalyzer("/tmp/hermes_structure.db")
analyzer.build_graph()

metrics = analyzer.get_centrality_metrics()
communities = analyzer.detect_communities()
bridges = analyzer.get_bridge_nodes(top_n=3)
```

### Monitoring & Anomaly Detection

```python
from domain.supporting.monitor import StateTracker, SnapshotAnomalyDetector

tracker = StateTracker("/tmp/hermes_structure.db")
detector = SnapshotAnomalyDetector("/tmp/hermes_structure.db")

snapshot = tracker.capture_snapshot()
anomalies = detector.detect_anomalies(snapshot)
```

## Architecture

```
domain/
  core/
    models.py              # SQLAlchemy ORM models (Project, Milestone, Skill, etc.)
    semantic_memory.py     # Semantic Memory -- ChromaDB vector store wrapper
    analyzer.py            # GraphAnalyzer -- centrality, communities, bridges
    graph.py               # RelationshipGraph -- NetworkX graph wrapper
    synthesis.py           # SynthesisEngine -- automated edge creation
    synthesizer.py         # InsightSynthesizer -- LLM narrative report generation
    insight_trigger.py     # Anomaly-to-orchestrator bridge
    agent.py               # Abstract agent base class
    agents_impl.py         # ResearcherAgent + AuditorAgent
    events.py              # Domain event definitions
    anomaly_detector.py    # Context-aware anomaly detection
    anomaly_config.py      # Threshold profiles and metric types
    refinement_engine.py   # Graph bloat and redundancy detection
    state_registry.py      # Context-aware state management
    semantic_ingestor.py   # LLM-powered semantic ingestion
    acl/                   # Anti-corruption layer translators
    ports/                 # Domain ports (BaseLLMInterface, GoalRunner, IntelligenceIngestor)
  supporting/
    ledger.py              # Structural Ledger -- CRUD for relational entities
    monitor.py             # StateTracker + AnomalyDetector
    monitor_models.py      # ORM models for snapshots and anomaly events
    config_loader.py       # YAML config loading

application/
  engine.py                # MemoryEngine -- ingestion, cross-layer query bridge
  orchestrator.py          # Agent lifecycle and goal decomposition
  autonomous_orchestrator.py # Autonomous orchestration with insight triggers
  refinement_orchestrator.py # Refinement proposal lifecycle

infrastructure/
  llm_interface.py         # Re-exports BaseLLMInterface from domain ports
  llm_implementations.py   # Local, Mock, OpenAI, and Template LLM backends
  youtube_content.py       # YouTube transcript fetcher (standalone utility)

scripts/
  execute_first_contact.py       # End-to-end integration demo
  stress_test_proactive_loop.py  # Anomaly detection stress test
  episodic_migration.py          # Batch migration from session logs
  test_llm_connectivity.py       # LLM backend connectivity check

tests/
  test_structural_bridge.py  # Cross-layer bridge tests
  test_orchestration.py      # Mock orchestration tests
  test_orchestration_real.py # Live LLM orchestration tests
  test_ingestion_loop.py     # Recursive learning loop tests
```

## Running Tests

```bash
# Unit tests (no LLM required)
python -m pytest tests/test_structural_bridge.py tests/test_orchestration.py

# Integration test (requires LLM backend configured)
python -m pytest tests/test_orchestration_real.py
```

## License

This project is licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later). See [LICENSE](LICENSE) for details.
