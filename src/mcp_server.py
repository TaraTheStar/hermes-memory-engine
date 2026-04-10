from mcp.server.fastmcp import FastMCP
import asyncio
import os
import sys

# Add the project root to sys.path so we can import the library
# The library is installed in editable mode or present in the path, 
# but for the MCP server to work as a standalone script, we need to ensure
# application and domain are importable.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from application.engine import MemoryEngine
except ImportError as e:
    print(f"Error importing MemoryEngine: {e}")
    sys.exit(1)

# Initialize FastMCP server
mcp = FastMCP("Hermes Memory")

# Initialize the actual Memory Engine
# We'll use some defaults for testing/prototype purposes
# In production, these would come from environment variables or config
SEMANTIC_DIR = os.getenv("HERMES_SEMANTIC_DIR", "/tmp/hermes_semantic")
STRUCTURAL_DB = os.getenv("HERMES_STRUCTURAL_DB", "/tmp/hermes_structure.db")

engine = MemoryEngine(
    semantic_dir=SEMANTIC_DIR,
    structural_db_path=STRUCTURAL_DB
)

@mcp.tool()
async def query_memory(query: str) -> str:
    """
    Perform a semantic search across the memory engine and return
    results enriched with structural context.
    """
    results = await asyncio.to_thread(engine.query, query)
    
    if not results:
        return "No relevant memories found."
    
    output = []
    for r in results:
        text = r.get("text", "")
        context = r.get("structural_context", "No structural context")
        output.append(f"Content: {text}\nContext: {context}")
    
    return "\n\n---\n\n".join(output)

@mcp.tool()
async def ingest_interaction(user_text: str, assistant_text: str) -> str:
    """
    Ingest a new interaction (user message and assistant response) into memory.
    The engine will automatically extract facts and events.
    """
    await asyncio.to_thread(
        engine.ingest_interaction,
        user_text=user_text,
        assistant_text=assistant_text,
    )
    return "Interaction successfully ingested and processed."

@mcp.tool()
async def add_project(name: str, url: str = None) -> str:
    """
    Add a new project to the structural ledger.
    """
    proj_id = await asyncio.to_thread(engine.ledger.add_project, name, url or "")
    return f"Project '{name}' added with ID: {proj_id}"

@mcp.tool()
async def add_milestone(project_id: int, name: str, description: str) -> str:
    """
    Add a milestone to an existing project.
    """
    ms_id = await asyncio.to_thread(
        engine.ledger.add_milestone, name, description, project_id=project_id
    )
    return f"Milestone '{name}' added to project {project_id} with ID: {ms_id}"

@mcp.tool()
async def get_knowledge_graph_insights() -> str:
    """
    Analyze the current memory graph and return high-level insights 
    (centrality, communities, and bridge nodes).
    """
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
            report.append(f"- Community {i+1}: {', '.join(map(str, comm[:10]))}...")

        report.append("\n#### Key Bridge Nodes (Connecting Domains):")
        for b in bridges:
            report.append(f"- {b}")

        return "\n".join(report)

    return await asyncio.to_thread(analyze)

if __name__ == "__main__":
    mcp.run()
