"""
Grace OS — Builtin Tools for the Unified Orchestrator.

These are Python-native tools that run locally (no MCP server needed).
They wrap existing Grace services (RAG, web search, web fetch) and expose
them in OpenAI function-calling format so the LLM can use them alongside
the MCP file/terminal tools.
"""

import json
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)


class BuiltinTool:
    """A single builtin tool with its schema and handler."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable,
        required_env: Optional[str] = None
    ):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.required_env = required_env

    def is_available(self) -> bool:
        """Check if this tool's dependencies are met."""
        if self.required_env:
            return bool(os.getenv(self.required_env))
        return True

    def to_openai_function(self) -> Dict[str, Any]:
        """Convert to OpenAI function-calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


# =============================================================================
# Tool Handlers
# =============================================================================

async def _handle_rag_search(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search the Grace knowledge base using semantic + keyword hybrid search."""
    query = arguments.get("query", "")
    limit = arguments.get("limit", 5)
    score_threshold = arguments.get("score_threshold", 0.3)

    if not query:
        return {"success": False, "content": "Error: 'query' parameter is required."}

    try:
        from retrieval.retriever import get_retriever
        from embedding import get_embedding_model
        from database.connection import DatabaseConnection
        from database.config import DatabaseConfig
        
        # Ensure database is initialized (crucial for standalone scripts)
        try:
            DatabaseConnection.get_engine()
        except RuntimeError:
            logger.info("[BUILTIN] Initializing database from environment...")
            DatabaseConnection.initialize(DatabaseConfig.from_env())
        
        # Get embedding model instance
        embedder = get_embedding_model()
        retriever = get_retriever(embedding_model=embedder)

        chunks = retriever.retrieve_hybrid(
            query=query,
            limit=limit,
            score_threshold=score_threshold
        )

        if not chunks:
            return {
                "success": True,
                "content": f"No relevant results found in the knowledge base for: '{query}'"
            }

        # Format results for the LLM
        results = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("metadata", {}).get("source", "unknown")
            score = chunk.get("score", 0)
            text = chunk.get("text", chunk.get("content", ""))
            results.append(f"[{i}] (score: {score:.2f}, source: {source})\n{text}")

        content = f"Found {len(results)} relevant results:\n\n" + "\n\n---\n\n".join(results)

        retriever.close()
        return {
            "success": True, 
            "content": content,
            "sources": [
                {
                    "source": chunk.get("metadata", {}).get("source", "unknown"),
                    "text": chunk.get("text", chunk.get("content", "")),
                    "score": chunk.get("score", 0),
                    "metadata": chunk.get("metadata", {})
                } for chunk in chunks
            ]
        }

    except Exception as e:
        logger.error(f"[BUILTIN] rag_search error: {e}")
        return {"success": False, "content": f"RAG search error: {str(e)}"}


async def _handle_web_search(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Search Google using SerpAPI."""
    query = arguments.get("query", "")
    num_results = arguments.get("num_results", 5)

    if not query:
        return {"success": False, "content": "Error: 'query' parameter is required."}

    api_key = os.getenv("SERPAPI_KEY", os.getenv("SERPAPI_API_KEY", ""))
    if not api_key:
        return {
            "success": False,
            "content": "Web search is not configured. Set SERPAPI_KEY in your .env file."
        }

    try:
        from search.serpapi_service import SerpAPIService
        service = SerpAPIService(api_key=api_key)
        results = service.search(query=query, num_results=num_results)

        if not results:
            return {"success": True, "content": f"No web results found for: '{query}'"}

        formatted = []
        for r in results:
            formatted.append(
                f"**{r['title']}**\n"
                f"URL: {r['link']}\n"
                f"{r.get('snippet', '')}"
            )

        content = f"Web search results for '{query}':\n\n" + "\n\n---\n\n".join(formatted)
        return {
            "success": True, 
            "content": content,
            "web_results": results
        }

    except Exception as e:
        logger.error(f"[BUILTIN] web_search error: {e}")
        return {"success": False, "content": f"Web search error: {str(e)}"}


async def _handle_web_fetch(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch and extract text content from a URL."""
    url = arguments.get("url", "")
    if not url:
        return {"success": False, "content": "Error: 'url' parameter is required."}

    try:
        import trafilatura

        logger.info(f"[BUILTIN] Fetching URL: {url}")
        downloaded = trafilatura.fetch_url(url)

        if not downloaded:
            return {"success": False, "content": f"Could not download content from: {url}"}

        content = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            output_format="txt"
        )

        if not content:
            return {"success": False, "content": f"Could not extract text from: {url}"}

        # Truncate very long pages to avoid context overflow
        max_chars = 8000
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n... [truncated, {len(content)} total chars]"

        return {"success": True, "content": f"Content from {url}:\n\n{content}"}

    except ImportError:
        return {"success": False, "content": "trafilatura is not installed. Run: pip install trafilatura"}
    except Exception as e:
        logger.error(f"[BUILTIN] web_fetch error: {e}")
        return {"success": False, "content": f"Web fetch error: {str(e)}"}


# =============================================================================
# Actuation Tool Handlers (Exposed from ConsensusActuation)
# =============================================================================

async def _handle_execute_shell_command(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a shell command via the consensus actuation gateway."""
    try:
        from cognitive.consensus_actuation import get_actuation_gateway
        gateway = get_actuation_gateway()
        result = gateway.execute_action(
            action_payload={
                "action_type": "execute_shell_command",
                "params": arguments,
                "rationale": arguments.get("rationale", "Autonomous system operation")
            },
            decision_context="Autonomous agent direct execution",
            trust_score=0.99  # High trust for autonomous local actions
        )
        return {"success": result.get("status") == "success", "content": json.dumps(result, indent=2)}
    except Exception as e:
        logger.error(f"[BUILTIN] execute_shell_command error: {e}")
        return {"success": False, "content": f"Shell command execution error: {str(e)}"}

async def _handle_submit_coding_task(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Submit an autonomous coding task directly to the agent queue."""
    try:
        from cognitive.consensus_actuation import get_actuation_gateway
        gateway = get_actuation_gateway()
        result = gateway.execute_action(
            action_payload={
                "action_type": "submit_coding_task",
                "params": arguments,
                "rationale": arguments.get("rationale", "Autonomous system operation")
            },
            decision_context="Autonomous agent direct execution",
            trust_score=0.99
        )
        return {"success": result.get("status") == "success", "content": json.dumps(result, indent=2)}
    except Exception as e:
        logger.error(f"[BUILTIN] submit_coding_task error: {e}")
        return {"success": False, "content": f"Submit coding task error: {str(e)}"}

async def _handle_restart_service(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Restart a system service / backend component."""
    try:
        from cognitive.consensus_actuation import get_actuation_gateway
        gateway = get_actuation_gateway()
        result = gateway.execute_action(
            action_payload={
                "action_type": "restart_service",
                "params": arguments,
                "rationale": arguments.get("rationale", "Autonomous system operation")
            },
            decision_context="Autonomous agent direct execution",
            trust_score=0.99
        )
        return {"success": result.get("status") == "success", "content": json.dumps(result, indent=2)}
    except Exception as e:
        logger.error(f"[BUILTIN] restart_service error: {e}")
        return {"success": False, "content": f"Restart service error: {str(e)}"}

async def _handle_update_knowledge_base(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Inject discovered knowledge or solutions directly into Unified Memory or Magma."""
    try:
        from cognitive.consensus_actuation import get_actuation_gateway
        gateway = get_actuation_gateway()
        result = gateway.execute_action(
            action_payload={
                "action_type": "update_knowledge_base",
                "params": arguments,
                "rationale": arguments.get("rationale", "Autonomous system operation")
            },
            decision_context="Autonomous agent direct execution",
            trust_score=0.99
        )
        return {"success": result.get("status") == "success", "content": json.dumps(result, indent=2)}
    except Exception as e:
        logger.error(f"[BUILTIN] update_knowledge_base error: {e}")
        return {"success": False, "content": f"Knowledge base update error: {str(e)}"}

# =============================================================================
# Tool Registry
# =============================================================================

def get_builtin_tools(
    enable_rag: bool = True,
    enable_web: bool = True
) -> List[BuiltinTool]:
    """
    Get all available builtin tools.

    Args:
        enable_rag: Include RAG knowledge search tool
        enable_web: Include web search and fetch tools
    """
    tools = []

    if enable_rag:
        tools.append(BuiltinTool(
            name="rag_search",
            description=(
                "Search the Grace knowledge base for information. This searches "
                "through all ingested documents, code, and data using semantic "
                "similarity. Use this when the user asks questions about their "
                "project, codebase, or previously ingested knowledge."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant knowledge"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                        "default": 5
                    },
                    "score_threshold": {
                        "type": "number",
                        "description": "Minimum relevance score 0-1 (default: 0.3)",
                        "default": 0.3
                    }
                },
                "required": ["query"]
            },
            handler=_handle_rag_search
        ))

    if enable_web:
        tools.append(BuiltinTool(
            name="web_search",
            description=(
                "Search Google for current information from the internet. "
                "Use this when the user needs up-to-date information, documentation, "
                "tutorials, or anything not in the local knowledge base."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The Google search query"
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            },
            handler=_handle_web_search,
            required_env="SERPAPI_KEY"
        ))

        tools.append(BuiltinTool(
            name="web_fetch",
            description=(
                "Fetch and extract the text content from a specific URL. "
                "Use this after web_search to read the full content of a page, "
                "or when the user provides a URL to read."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch and extract content from"
                    }
                },
                "required": ["url"]
            },
            handler=_handle_web_fetch
        ))

    # Add Consensus Actuation endpoints
    tools.append(BuiltinTool(
        name="execute_shell_command",
        description=(
            "Execute a robust shell command via the consensus actuation gateway. "
            "Allows the agent to actuate physical commands like `ls`, `grep`, or process inspection."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute"
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this action is being taken"
                }
            },
            "required": ["command"]
        },
        handler=_handle_execute_shell_command
    ))

    tools.append(BuiltinTool(
        name="submit_coding_task",
        description=(
            "Submit an autonomous coding task directly to the agent queue to resolve a code-level error. "
            "Specify instructions and an optional target file."
        ),
        parameters={
            "type": "object",
            "properties": {
                "instructions": {
                    "type": "string",
                    "description": "Detailed instructions for the coding task"
                },
                "target_file": {
                    "type": "string",
                    "description": "The specific file to target (if any)"
                },
                "error_class": {
                    "type": "string",
                    "description": "Optional error classification for tracking"
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this action is being taken"
                }
            },
            "required": ["instructions"]
        },
        handler=_handle_submit_coding_task
    ))

    tools.append(BuiltinTool(
        name="restart_service",
        description=(
            "Restart a specific system service, component or process, such as `backend`. "
        ),
        parameters={
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Target service to restart (e.g. 'backend', 'worker', 'database', 'cache')"
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this action is being taken"
                }
            },
            "required": ["target"]
        },
        handler=_handle_restart_service
    ))

    tools.append(BuiltinTool(
        name="update_knowledge_base",
        description=(
            "Inject a discovered rule, solution, or system pattern directly into the system's runtime memory."
        ),
        parameters={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The raw knowledge/solution to store"
                },
                "pattern_type": {
                    "type": "string",
                    "description": "Optional category of the knowledge (e.g., 'consensus_learning')"
                },
                "rationale": {
                    "type": "string",
                    "description": "Why this action is being taken"
                }
            },
            "required": ["content"]
        },
        handler=_handle_update_knowledge_base
    ))

    return tools
