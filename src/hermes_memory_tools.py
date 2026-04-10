import os
import sys
import asyncio
import json

# Add the project root to sys.path so we can import the library
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from application.engine import MemoryEngine
except ImportError as e:
    print(f"Error importing MemoryEngine: {e}")
    sys.exit(1)

# Import the Hermes Agent registry
# We assume the user has hermes-agent in their path or it's available in the environment
try:
    from tools.registry import registry, tool_result, tool_error
except ImportError:
    # Fallback for development/testing if hermes-agent isn't installed as a package
    # We'll try to find it in the repos directory if possible
    import importlib.util
    agent_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../repos/hermes-agent"))
    if agent_path not in sys.path:
        sys.path.append(agent_path)
    
    try:
        from tools.registry import registry, tool_result, tool_error
    except ImportError as e:
        print(f"Could not find hermes-agent registry. Please ensure hermes-agent is in your PYTHONPATH. Error: {e}")
        sys.exit(1)

# Initialize the Memory Engine
SEMANTIC_DIR = os.getenv("HERMES_SEMANTIC_DIR", "/tmp/hermes_semantic")
STRUCTURAL_DB = os.getenv("HERMES_STRUCTURAL_DB", "/tmp/hermes_structure.db")

engine = MemoryEngine(
    semantic_dir=SEMANTIC_DIR,
    structural_db_path=STRUCTURAL_DB
)

# ---------------------------------------------------------------------------
# Tool Handlers
# ---------------------------------------------------------------------------

async def handle_query_memory(args: dict, **kwargs) -> str:
    """Handler for searching memory."""
    query = args.get("query")
    if not query:
        return tool_error("Missing required parameter: 'query'")
    
    results = await asyncio.to_thread(engine.query, query)
    
    if not results:
        return tool_result({"message": "No relevant memories found."})
    
    formatted_results = []
    for r in results:
        text = r.get("text", "")
        context = r.get("structural_context", "No structural context")
        formatted_results.append(f"Content: {text}\nContext: {context}")
    
    return tool_result({"results": "\n\n---\n\n".join(formatted_results)})

async def handle_ingest_interaction(args: dict, **kwargs) -> str:
    """Handler for ingesting a user/assistant turn."""
    user_text = args.get("user_text")
    assistant_text = args.get("assistant_text")
    
    if not user_text or not assistant_text:
        return tool_error("Both 'user_text' and 'assistant_text' are required.")
    
    await asyncio.to_thread(
        engine.ingest_interaction,
        user_text=user_text,
        assistant_text=assistant_text,
    )
    return tool_result({"status": "success", "message": "Interaction ingested."})

async def handle_add_project(args: dict, **kwargs) -> str:
    """Handler for adding a project."""
    name = args.get("name")
    url = args.get("url", "")
    
    if not name:
        return tool_error("Missing required parameter: 'name'")
    
    proj_id = await asyncio.to_thread(engine.ledger.add_project, name, url)
    return tool_result({"status": "success", "project_id": proj_id, "name": name})

async def handle_add_milestone(args: dict, **kwargs) -> str:
    """Handler for adding a milestone."""
    project_id = args.get("project_id")
    name = args.get("name")
    description = args.get("description", "")
    
    if project_id is None or not name:
        return tool_error("Both 'project_id' and 'name' are required.")
    
    ms_id = await asyncio.to_thread(
        engine.ledger.add_milestone, name, description, project_id=int(project_id)
    )
    return tool_result({"status": "success", "milestone_id": ms_id, "name": name})

async def handle_get_insights(args: dict, **kwargs) -> str:
    """Handler for getting graph insights."""
    from domain.core.analyzer import GraphAnalyzer
    
    def analyze():
        analyzer = GraphAnalyzer(STRUCTURAL_DB)
        analyzer.build_graph()
        metrics = analyzer.get_centrality_metrics()
        communities = analyzer.detect_communities()
        bridges = analyzer.get_bridge_nodes(top_n=3)

        report = ["### Knowledge Graph Insights"]
        report.append("\n#### Top Central Nodes:")
        for node, score in list(metrics.items())[:5]:
            report.append(f"- {node}: {score:.4f}")
        report.append("\n#### Communities Detected:")
        for i, comm in enumerate(communities):
            report.append(f"- Community {i+1}: {', '.join(map(str, comm[:5]))}...")
        report.append("\n#### Key Bridge Nodes:")
        for b in bridges:
            report.append(f"- {b}")
        return "\n".join(report)

    insight_text = await asyncio.to_thread(analyze)
    return tool_result({"insights": insight_text})

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

# Define the schemas for the Hermes Agent registry
QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "The semantic query to perform in memory."}
    },
    "required": ["query"],
    "description": "Search the memory engine for semantic and structural context."
}

INGEST_SCHEMA = {
    "type": "object",
    "properties": {
        "user_text": {"type": "string", "description": "The user's message."},
        "assistant_text": {"type": "string", "description": "The assistant's response."}
    },
    "required": ["user_text", "assistant_text"],
    "description": "Ingest a conversation turn into the memory engine."
}

PROJECT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "The name of the project."},
        "url": {"type": "string", "description": "The URL of the project repository."}
    },
    "required": ["name"],
    "description": "Add a new project to the structural ledger."
}

MILESTONE_SCHEMA = {
    "type": "object",
    "properties": {
        "project_id": {"type": "integer", "description": "The ID of the project."},
        "name": {"type": "string", "description": "The name of the milestone."},
        "description": {"type": "string", "description": "A description of the milestone."}
    },
    "required": ["project_id", "name"],
    "description": "Add a milestone to an existing project."
}

INSIGHTS_SCHEMA = {
    "type": "object",
    "properties": {},
    "description": "Retrieve high-level insights from the current knowledge graph."
}

# Register all tools into the Hermes toolset
registry.register(
    name="query_memory",
    toolset="memory",
    schema=QUERY_SCHEMA,
    handler=handle_query_memory,
    is_async=True,
    description="Search memory for semantic and structural context.",
    emoji="🧠"
)

registry.register(
    name="ingest_interaction",
    toolset="memory",
    schema=INGEST_SCHEMA,
    handler=handle_ingest_interaction,
    is_async=True,
    description="Ingest a conversation turn into memory.",
    emoji="📥"
)

registry.register(
    name="add_project",
    toolset="memory",
    schema=PROJECT_SCHEMA,
    handler=handle_add_project,
    is_async=True,
    description="Add a new project to the structural ledger.",
    emoji="📁"
)

registry.register(
    name="add_milestone",
    toolset="memory",
    schema=MILESTONE_SCHEMA,
    handler=handle_add_milestone,
    is_async=True,
    description="Add a milestone to an existing project.",
    emoji="🚩"
)

registry.register(
    name="get_insights",
    toolset="memory",
    schema=INSIGHTS_SCHEMA,
    handler=handle_get_insights,
    is_async=True,
    description="Retrieve knowledge graph insights (centrality, communities, etc.).",
    emoji="📈"
)

print("Successfully registered Hermes Memory Toolset to registry.")
