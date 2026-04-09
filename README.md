# Hermes Memory Engine

A dual-layer memory engine that combines relational fact storage with vector-based semantic search. Hermes bridges structured knowledge (projects, milestones, skills, identity markers) with unstructured semantic events, enabling rich contextual recall and graph-based insight generation.

**Now supporting both MCP (Model Context Protocol) and Native Hermes-Agent toolsets.**

## Features

- **Dual-Layer Architecture**
  - **Structural Ledger** -- SQLite-backed relational storage for entities and relationships via SQLAlchemy.
  - **Semantic Memory** -- ChromaDB vector store for embedding-based conceptual search.
  - **Cross-Layer Bridge** -- Queries enrich semantic results with structural context and graph neighbors.
- **Intelligence & Analysis**
  - **Graph Analysis** -- Centrality metrics, community detection, and bridge node identification via NetworkX.
  - **Synthesis Engine** -- Automated edge creation through temporal correlation, semantic co-occurrence, and attribute symmetry scans.
  - **Insight Synthesis** -- LLM-powered narrative reports translating graph metrics into human-readable insights.
  - **Monitoring & Anomaly Detection** -- Periodic graph snapshots with statistical anomaly detection (hub emergence, community shifts).
- **Deployment Modes**
  - **MCP Server** -- A standalone server providing memory capabilities to any MCP-compliant client.
  - **Native Toolset** -- High-performance, direct-integration tools designed specifically for `hermes-agent`.

## Installation

Requires Python 3.10+.

```bash
git clone <repo-url>
cd hermes-memory-engine
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

## Integration

### 1. MCP Server (Standard)
Run the server as a subprocess via MCP transport. Configure your client (e.g., `hermes-agent`) via the `mcp_servers` key in your config:

```yaml
mcp_servers:
  hermes_memory:
    command: "python"
    args: ["/path/to/hermes-memory-engine/src/mcp_server.py"]
    env:
      HERMES_SEMANTIC_DIR: "/path/to/semantic"
      HERMES_STRUCTURAL_DB: "/path/to/structure.db"
```

### 2. Native Toolset (High Performance)
For direct integration into `hermes-agent`, import the toolset directly in your agent's initialization:

```python
from hermes_memory_engine.src.hermes_memory_tools import registry

# The tools are automatically registered with the hermes-agent registry
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `HERMES_STRUCTURAL_DB` | Path to the SQLite database | `/data/hermes_memory_engine/structural/structure.db` |
| `HERMES_SEMANTIC_DIR` | Path to the ChromaDB storage directory | `/data/hermes_memory_engine/semantic/chroma_db` |

## Architecture

```
domain/
  core/
    models.py              # SQLAlchemy ORM models
    semantic_memory.py     # ChromaDB vector store wrapper
    analyzer.py            # GraphAnalyzer (centrality, communities, bridges)
    graph.py               # RelationshipGraph wrapper
    synthesis.py           # SynthesisEngine (automated edge creation)
    synthesizer.py         # InsightSynthesizer (LLM narrative reports)
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
    ports/                 # Domain ports (BaseLLMInterface, GoalRunner, etc.)
  supporting/
    ledger.py              # Structural Ledger (CRUD for relational entities)
    monitor.py             # StateTracker + AnomalyDetector
    monitor_models.py      # ORM models for snapshots and anomaly events
    config_loader.py       # YAML config loading

application/
  engine.py                # MemoryEngine (The primary entry point)
  orchestrator.py          # Agent lifecycle and goal decomposition
  autonomous_orchestrator.py # Autonomous orchestration with insight triggers
  refinement_orchestrator.py # Refinement proposal lifecycle

infrastructure/
  llm_interface.py         # Re-exports BaseLLMInterface
  llm_implementations.py   # Local, Mock, OpenAI, and Template LLM backends
  youtube_content.py       # YouTube transcript fetcher

src/
  mcp_server.py            # FastMCP implementation for MCP clients
  hermes_memory_tools.py   # Native toolset for hermes-agent registry

utils/
  execute_first_contact.py       # End-to-end integration demo
  stress_test_proactive_loop.py  # Anomaly detection stress test
  episodic_migration.py          # Batch migration from session logs
  test_llm_connectivity.py       # LLM backend connectivity check

tests/
  ... (comprehensive test suite)
```

## License

This project is licensed under the GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later).
