"""
Grace OS — Unified Orchestrator.

Manages the multi-turn interaction loop between the LLM and ALL tools:
- MCP tools (file I/O, terminal, search) → routed to DesktopCommanderMCP server
- Builtin tools (RAG, web search, web fetch) → executed locally in Python

The LLM receives all tools at once and decides which to use at each step.
No keyword routing or pre-classification — the LLM is the router.

Compatible with both OpenAI and Ollama (via tool-calling API).
"""

import asyncio
import json
import logging
import os
import time
import uuid
import requests
from typing import Any, Dict, List, Optional, Callable

from grace_mcp.client import MCPClient
from grace_mcp.audit_logger import AuditLogger
from grace_mcp.builtin_tools import get_builtin_tools, BuiltinTool

logger = logging.getLogger(__name__)

# Maximum number of tool-calling turns to prevent infinite loops
MAX_TOOL_TURNS = 10


class MCPOrchestrator:
    """
    Orchestrates multi-turn tool-calling conversations.
    
    This is the central nervous system for Grace OS MCP integration.
    It connects the LLM (OpenAI / Ollama) with MCP tools (file I/O, terminal, git).
    
    Usage:
        orchestrator = MCPOrchestrator()
        await orchestrator.initialize()
        response = await orchestrator.chat(
            messages=[{"role": "user", "content": "Read the file app.py"}],
            model="gpt-4o"
        )
    """

    def __init__(
        self,
        mcp_client: MCPClient = None,
        llm_provider: str = None,
        llm_api_key: str = None,
        llm_base_url: str = None,
        llm_model: str = None,
        max_tool_turns: int = MAX_TOOL_TURNS,
        system_prompt: str = None,
        enable_rag: bool = True,
        enable_web: bool = True
    ):
        self.mcp_client = mcp_client or MCPClient()
        
        # LLM configuration — read from env if not provided
        self.llm_provider = llm_provider or os.getenv("LLM_PROVIDER", "openai")
        self.llm_api_key = llm_api_key or os.getenv("LLM_API_KEY", "")
        self.llm_model = llm_model or os.getenv("LLM_MODEL", "gpt-4o")
        self.llm_base_url = llm_base_url or self._get_default_base_url()
        
        self.max_tool_turns = max_tool_turns
        self.system_prompt = system_prompt or self._default_system_prompt()
        
        # Builtin tools (RAG, web search, web fetch)
        self._builtin_tools: Dict[str, BuiltinTool] = {}
        self._enable_rag = enable_rag
        self._enable_web = enable_web
        
        self._initialized = False
        self._tools_openai_format = []

    def _get_default_base_url(self) -> str:
        """Get the default base URL for the configured LLM provider."""
        if self.llm_provider == "openai":
            return "https://api.openai.com/v1"
        else:
            return os.getenv("OLLAMA_URL", "http://localhost:11434") + "/v1"

    def _default_system_prompt(self) -> str:
        import platform
        cwd = os.getcwd()
        os_info = platform.system()
        
        return (
            f"You are Grace OS, an AI coding assistant running on {os_info}. "
            "You have direct access to the local file system, terminal, "
            "knowledge base, and the internet.\n\n"
            f"Your current working directory is: {cwd}\n\n"
            "You have the following capabilities:\n"
            "- **File Operations**: read, write, edit, move, search files and directories\n"
            "- **Terminal**: execute commands, manage processes\n"
            "- **Knowledge Base**: search ingested documents via rag_search\n"
            "- **Web**: search Google via web_search, fetch page content via web_fetch\n"
            "- **Resources**: read real-time data streams via read_resource (e.g., logs://{pid} for process output)\n\n"
            "The LLM decides which tools to use based on context. "
            "For example, a single request might require web_search followed by write_file.\n\n"
            "Rules:\n"
            "- Use logs://{pid} with read_resource to monitor the real-time output of a process without starting a new one\n"
            "- Use rag_search when the user asks about their project or knowledge base\n"
            "- Use web_search for current information not in the knowledge base\n"
            "- Use web_fetch to read the full content of a specific URL\n"
            "- Always read a file before editing it\n"
            "- Use edit_block for surgical edits (search/replace)\n"
            "- Use write_file only for creating new files or full rewrites\n"
            "- Use paths relative to the current directory\n"
            "- Never delete files without explicit user confirmation\n"
        )

    async def initialize(self) -> bool:
        """Initialize the orchestrator by connecting to the MCP server and registering builtin tools."""
        try:
            logger.info("[ORCHESTRATOR] Initializing MCP connection...")
            connected = await self.mcp_client.connect()
            
            if not connected:
                logger.error("[ORCHESTRATOR] Failed to connect to MCP server")
                return False

            # Get MCP tools in OpenAI function-calling format
            self._tools_openai_format = self.mcp_client.get_tools_as_openai_functions()
            
            # Add virtual read_resource tool for the LLM
            self._tools_openai_format.append({
                "type": "function",
                "function": {
                    "name": "read_resource",
                    "description": (
                        "Read a real-time data resource from the system via a URI. "
                        "Currently supports Process Logs using the logs://{pid} format. "
                        "Use this to monitor the output of a running process or check logs "
                        "without repeatedly calling tools."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "uri": {
                                "type": "string",
                                "description": "The URI of the resource to read (e.g., logs://1234)"
                            }
                        },
                        "required": ["uri"]
                    }
                }
            })
            
            mcp_count = len(self._tools_openai_format)

            # Register builtin tools (RAG, web search, web fetch)
            builtin_tools = get_builtin_tools(
                enable_rag=self._enable_rag,
                enable_web=self._enable_web
            )
            for tool in builtin_tools:
                if tool.is_available():
                    self._builtin_tools[tool.name] = tool
                    self._tools_openai_format.append(tool.to_openai_function())
                    logger.info(f"[ORCHESTRATOR] Registered builtin tool: {tool.name}")
                else:
                    logger.warning(f"[ORCHESTRATOR] Builtin tool '{tool.name}' unavailable (missing env)")

            builtin_count = len(self._builtin_tools)
            total_count = len(self._tools_openai_format)
            logger.info(
                f"[ORCHESTRATOR] ✅ Ready with {total_count} tools "
                f"({mcp_count} MCP + {builtin_count} builtin)"
            )
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"[ORCHESTRATOR] Initialization failed: {e}")
            return False

    async def shutdown(self):
        """Shutdown the orchestrator and disconnect from MCP."""
        await self.mcp_client.disconnect()
        self._initialized = False
        logger.info("[ORCHESTRATOR] Shut down")

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        calling_layer: str = "user",
        session_id: str = None,
        on_tool_call: Callable = None
    ) -> Dict[str, Any]:
        """
        Run a multi-turn tool-calling conversation.
        
        Args:
            messages: Conversation messages (OpenAI format)
            model: LLM model to use
            temperature: Sampling temperature
            max_tokens: Max response tokens
            calling_layer: Which Grace OS layer is calling
            session_id: Session tracking ID
            on_tool_call: Optional callback for each tool call (for streaming updates)
            
        Returns:
            Dict with 'content', 'tool_calls_made', 'turns', 'model'
        """
        if not self._initialized:
            success = await self.initialize()
            if not success:
                return {
                    "content": "Error: MCP server is not available. Please check the server.",
                    "tool_calls_made": [],
                    "turns": 0,
                    "success": False
                }

        model = model or self.llm_model
        session_id = session_id or str(uuid.uuid4())
        
        # Prepare messages with system prompt
        full_messages = []
        if self.system_prompt:
            full_messages.append({"role": "system", "content": self.system_prompt})
        full_messages.extend(messages)

        all_tool_calls = []
        all_sources = []
        turn = 0

        while turn < self.max_tool_turns:
            turn += 1
            logger.info(f"[ORCHESTRATOR] Turn {turn}/{self.max_tool_turns}")

            # Call the LLM
            llm_response = await self._call_llm(
                messages=full_messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=self._tools_openai_format
            )

            if not llm_response["success"]:
                return {
                    "content": f"LLM Error: {llm_response.get('error', 'Unknown error')}",
                    "tool_calls_made": all_tool_calls,
                    "turns": turn,
                    "success": False
                }

            response_message = llm_response["message"]
            
            # Check if the LLM wants to call tools
            tool_calls = response_message.get("tool_calls", [])
            
            if not tool_calls:
                # No tool calls — this is the final response
                final_content = response_message.get("content", "")
                return {
                    "content": final_content,
                    "tool_calls_made": all_tool_calls,
                    "sources": all_sources,
                    "turns": turn,
                    "model": model,
                    "success": True
                }

            # Add assistant message with tool calls to conversation
            full_messages.append(response_message)

            # Execute each tool call
            for tc in tool_calls:
                func_name = tc["function"]["name"]
                func_args_str = tc["function"]["arguments"]
                tool_call_id = tc["id"]

                try:
                    func_args = json.loads(func_args_str) if isinstance(func_args_str, str) else func_args_str
                except json.JSONDecodeError:
                    func_args = {}

                logger.info(f"[ORCHESTRATOR] 🔧 Tool call: {func_name}")

                # Notify callback if provided
                if on_tool_call:
                    on_tool_call(func_name, func_args)

                # Route: builtin tools run locally, MCP tools go to server
                start_time = time.time()
                if func_name in self._builtin_tools:
                    # Execute builtin tool locally
                    result = await self._builtin_tools[func_name].handler(func_args)
                    duration_ms = (time.time() - start_time) * 1000
                    result["duration_ms"] = duration_ms
                    logger.info(f"[ORCHESTRATOR] Builtin '{func_name}' completed in {duration_ms:.0f}ms")
                elif func_name == "read_resource":
                    # Execute resource read via MCP client
                    uri = func_args.get("uri")
                    result = await self.mcp_client.read_resource(uri)
                    duration_ms = (time.time() - start_time) * 1000
                    result["duration_ms"] = duration_ms
                    
                    # Log resource read to audit trail
                    self.mcp_client.audit_logger.log_resource_read(
                        uri=uri,
                        duration_ms=duration_ms,
                        calling_layer="orchestrator",
                        session_id=session_id,
                        success=result.get("success", False),
                        error=result.get("error")
                    )
                    logger.info(f"[ORCHESTRATOR] Resource read '{uri}' completed in {duration_ms:.0f}ms")
                else:
                    # Execute via MCP server
                    result = await self.mcp_client.call_tool(
                        tool_name=func_name,
                        arguments=func_args,
                        calling_layer=calling_layer,
                        session_id=session_id
                    )

                tool_result_content = result.get("content", "")
                all_tool_calls.append({
                    "tool": func_name,
                    "arguments": func_args,
                    "result_preview": tool_result_content[:200],
                    "success": result.get("success", False),
                    "duration_ms": result.get("duration_ms", 0)
                })

                # Collect sources if this was a RAG search
                if "sources" in result:
                    all_sources.extend(result["sources"])

                # Add tool result to conversation for the LLM's next turn
                full_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": tool_result_content
                })

        # Max turns exceeded
        return {
            "content": f"Reached maximum tool-calling turns ({self.max_tool_turns}). "
                       "The operation may be incomplete.",
            "tool_calls_made": all_tool_calls,
            "sources": all_sources,
            "turns": turn,
            "model": model,
            "success": False
        }

    async def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float,
        max_tokens: int,
        tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Call the LLM with tool definitions.
        Supports both OpenAI and Ollama (via OpenAI-compatible API).
        """
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            if self.llm_provider == "openai":
                headers["Authorization"] = f"Bearer {self.llm_api_key}"

            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            # Only include tools if we have them
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            url = f"{self.llm_base_url}/chat/completions"
            
            logger.debug(f"[ORCHESTRATOR] LLM request to {url} with model {model}")

            # Run the blocking HTTP call in a thread to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=120
                )
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"[ORCHESTRATOR] LLM error ({response.status_code}): {error_text}")
                return {
                    "success": False,
                    "error": f"LLM API error {response.status_code}: {error_text}",
                    "message": {}
                }

            result = response.json()
            message = result["choices"][0]["message"]

            return {
                "success": True,
                "message": message
            }

        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "LLM request timed out after 120s",
                "message": {}
            }
        except Exception as e:
            logger.error(f"[ORCHESTRATOR] LLM call failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": {}
            }

    async def read_resource(self, uri: str, session_id: str = None) -> Dict[str, Any]:
        """
        Read an MCP resource by URI.
        
        Args:
            uri: The resource URI to read.
            session_id: Optional session identifier for auditing.
            
        Returns:
            Dict containing the resource content or error details.
        """
        start_time = time.time()
        result = await self.mcp_client.read_resource(uri)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log resource read to audit trail
        self.mcp_client.audit_logger.log_resource_read(
            uri=uri,
            duration_ms=duration_ms,
            calling_layer="orchestrator_direct",
            session_id=session_id,
            success=result.get("success", False),
            error=result.get("error")
        )
        
        return result

    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        return {
            "initialized": self._initialized,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "tools_total": len(self._tools_openai_format),
            "tools_mcp": len(self._tools_openai_format) - len(self._builtin_tools),
            "tools_builtin": list(self._builtin_tools.keys()),
            "max_tool_turns": self.max_tool_turns,
            "mcp_client": self.mcp_client.get_status()
        }


# Global instance
_orchestrator: Optional[MCPOrchestrator] = None


async def get_mcp_orchestrator() -> MCPOrchestrator:
    """Get or create the global MCPOrchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MCPOrchestrator()
        await _orchestrator.initialize()
    return _orchestrator


def get_mcp_orchestrator_sync() -> MCPOrchestrator:
    """Get the global MCPOrchestrator instance without initializing (for sync code)."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MCPOrchestrator()
    return _orchestrator
