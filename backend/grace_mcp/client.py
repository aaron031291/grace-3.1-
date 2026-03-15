"""
Grace OS — MCP Client.

Connects to DesktopCommanderMCP (or any MCP server) via stdio transport.
Provides methods to discover tools, call tools, and manage the connection.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from grace_mcp.audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP Client that connects to DesktopCommanderMCP via stdio transport.
    
    Usage:
        client = MCPClient()
        await client.connect()
        tools = await client.list_tools()
        result = await client.call_tool("read_file", {"path": "/some/file.py"})
        await client.disconnect()
    """

    def __init__(
        self,
        server_command: str = None,
        server_args: List[str] = None,
        audit_logger: AuditLogger = None,
        allowed_directories: List[str] = None
    ):
        # Path to the DesktopCommanderMCP built JS entry point
        if server_command is None:
            # Look in multiple locations for robustness during migration/Docker
            possible_roots = [
                Path(__file__).parent.parent,           # backend/
                Path(__file__).parent.parent.parent    # root/ (old location)
            ]
            
            mcp_repo_path = None
            for root in possible_roots:
                potential_path = root / "mcp_repos" / "DesktopCommanderMCP"
                if potential_path.exists():
                    mcp_repo_path = potential_path
                    break
            
            if not mcp_repo_path:
                logger.warning("[MCP] Could not find DesktopCommanderMCP directory automatically")
                # Default to root-relative for fallback
                mcp_repo_path = Path(__file__).parent.parent.parent / "mcp_repos" / "DesktopCommanderMCP"

            server_command = "node"
            server_args = [str(mcp_repo_path / "dist" / "index.js")]
        
        self.server_command = server_command
        self.server_args = server_args or []
        self.audit_logger = audit_logger or AuditLogger()
        self.allowed_directories = allowed_directories or []
        
        self._session: Optional[ClientSession] = None
        self._tools_cache: Optional[List[Dict]] = None
        self._connected = False
        self._read = None
        self._write = None
        self._cm = None  # context manager for stdio_client

        # Layer permission enforcement
        self._permissions_path = Path(__file__).parent.parent / "grace_os" / "config" / "layer_permissions.yaml"
        self._layer_permissions = self._load_layer_permissions()

    def _load_layer_permissions(self) -> Dict[str, List[str]]:
        """Load layer->tool permission map from YAML."""
        try:
            with open(self._permissions_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
            perms = {}
            for layer_name, cfg in raw.items():
                if isinstance(cfg, dict):
                    perms[layer_name] = cfg.get("allowed_tools", [])
            return perms
        except Exception as e:
            logger.error(f"[MCP] Failed to load layer permissions: {e}")
            return {}

    def _is_tool_allowed(self, calling_layer: str, tool_name: str) -> bool:
        """Check if calling_layer is permitted to use tool_name."""
        # "user" and unknown callers bypass layer enforcement
        if calling_layer in ("user", "system", "admin"):
            return True
        allowed = self._layer_permissions.get(calling_layer, None)
        if allowed is None:
            return True  # Unknown layer — not a Grace OS layer, allow
        # Normalize: YAML uses file_read, MCP uses read_file — check both forms
        tool_normalized = tool_name.replace("-", "_")
        parts = tool_normalized.split("_", 1)
        tool_flipped = f"{parts[1]}_{parts[0]}" if len(parts) == 2 else tool_normalized
        return tool_normalized in allowed or tool_flipped in allowed or tool_name in allowed

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Connect to the MCP server via stdio transport."""
        try:
            server_params = StdioServerParameters(
                command=self.server_command,
                args=self.server_args,
                env={
                    **os.environ,
                    "NODE_NO_WARNINGS": "1"
                }
            )

            logger.info(
                f"[MCP] Connecting to server: {self.server_command} {' '.join(self.server_args)}"
            )

            # Create the stdio connection
            self._cm = stdio_client(server_params)
            self._read, self._write = await self._cm.__aenter__()

            # Initialize the session
            self._session = ClientSession(self._read, self._write)
            await self._session.__aenter__()
            await self._session.initialize()

            self._connected = True
            
            # Cache available tools
            await self._refresh_tools_cache()
            
            logger.info(
                f"[MCP] ✅ Connected! {len(self._tools_cache)} tools available"
            )
            return True

        except Exception as e:
            logger.error(f"[MCP] ❌ Failed to connect: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        """Disconnect from the MCP server."""
        try:
            if self._session:
                await self._session.__aexit__(None, None, None)
            if self._cm:
                await self._cm.__aexit__(None, None, None)
            self._connected = False
            self._session = None
            self._tools_cache = None
            logger.info("[MCP] Disconnected")
        except Exception as e:
            logger.error(f"[MCP] Error during disconnect: {e}")

    async def _refresh_tools_cache(self):
        """Fetch and cache the list of available tools."""
        if not self._session:
            return
        result = await self._session.list_tools()
        self._tools_cache = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
            }
            for tool in result.tools
        ]

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available MCP resources."""
        if not self._session:
            return []
        result = await self._session.list_resources()
        return [
            {
                "uri": r.uri,
                "name": r.name,
                "description": r.description or "",
                "mime_type": r.mimeType or ""
            }
            for r in result.resources
        ]

    async def list_resource_templates(self) -> List[Dict[str, Any]]:
        """List available MCP resource templates."""
        if not self._session:
            return []
        result = await self._session.list_resource_templates()
        return [
            {
                "uri_template": t.uriTemplate,
                "name": t.name,
                "description": t.description or "",
                "mime_type": t.mimeType or ""
            }
            for t in result.resourceTemplates
        ]

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read an MCP resource by URI."""
        if not self._session:
            return {"content": "", "success": False, "error": "Not connected"}
        
        try:
            result = await self._session.read_resource(uri)
            content_parts = []
            for content in result.contents:
                if hasattr(content, 'text') and content.text:
                    content_parts.append(content.text)
                elif hasattr(content, 'blob') and content.blob:
                    content_parts.append(f"[Binary data: {content.mimeType}]")
            
            return {
                "content": "\n".join(content_parts),
                "success": True
            }
        except Exception as e:
            logger.error(f"[MCP] Failed to read resource {uri}: {e}")
            return {"content": "", "success": False, "error": str(e)}

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools."""
        if self._tools_cache is None:
            await self._refresh_tools_cache()
        return self._tools_cache or []

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        calling_layer: str = "user",
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        Call an MCP tool and return the result.
        
        Args:
            tool_name: Name of the MCP tool (e.g. 'read_file', 'write_file')
            arguments: Tool arguments dict
            calling_layer: Which Grace OS layer is calling (for audit/permissions)
            session_id: Session ID for tracking
            
        Returns:
            Dict with 'content', 'success', and 'error' keys
        """
        if not self._connected or not self._session:
            return {
                "content": "",
                "success": False,
                "error": "MCP client not connected"
            }

        # Layer permission enforcement
        if not self._is_tool_allowed(calling_layer, tool_name):
            error_msg = f"DENIED: Tool '{tool_name}' not permitted for layer '{calling_layer}'"
            logger.warning(f"[MCP] {error_msg}")
            self.audit_logger.log_tool_call(
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                duration_ms=0,
                calling_layer=calling_layer,
                session_id=session_id,
                success=False,
                error=error_msg
            )
            return {"content": "", "success": False, "error": error_msg, "duration_ms": 0}

        start_time = time.time()
        
        try:
            logger.info(f"[MCP] Calling tool: {tool_name}")
            logger.debug(f"[MCP] Arguments: {json.dumps(arguments, default=str)[:500]}")

            result = await self._session.call_tool(tool_name, arguments)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract text content from the result
            content_parts = []
            if hasattr(result, 'content') and result.content:
                for part in result.content:
                    if hasattr(part, 'text'):
                        content_parts.append(part.text)
                    elif hasattr(part, 'data'):
                        content_parts.append(str(part.data))
            
            content = "\n".join(content_parts) if content_parts else str(result)
            is_error = getattr(result, 'isError', False)

            # Log to audit trail
            self.audit_logger.log_tool_call(
                tool_name=tool_name,
                arguments=arguments,
                result=content[:500],
                duration_ms=duration_ms,
                calling_layer=calling_layer,
                session_id=session_id,
                success=not is_error,
                error=content if is_error else None
            )

            return {
                "content": content,
                "success": not is_error,
                "error": content if is_error else None,
                "duration_ms": duration_ms
            }

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            
            self.audit_logger.log_tool_call(
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                duration_ms=duration_ms,
                calling_layer=calling_layer,
                session_id=session_id,
                success=False,
                error=error_msg
            )

            logger.error(f"[MCP] Tool call failed: {tool_name} — {error_msg}")
            return {
                "content": "",
                "success": False,
                "error": error_msg,
                "duration_ms": duration_ms
            }

    def get_tools_as_openai_functions(self) -> List[Dict[str, Any]]:
        """
        Convert cached MCP tools into OpenAI function-calling format.
        This is the bridge between MCP tool definitions and LLM tool calling.
        
        Returns:
            List of OpenAI-compatible tool definitions
        """
        if not self._tools_cache:
            return []

        openai_tools = []
        for tool in self._tools_cache:
            # Skip internal/config tools that the LLM shouldn't call directly
            skip_tools = {
                "get_config", "set_config_value", "get_usage_stats",
                "give_feedback_to_desktop_commander", "get_recent_tool_calls",
                "list_searches", "get_more_search_results", "stop_search"
            }
            if tool["name"] in skip_tools:
                continue

            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("input_schema", {
                        "type": "object",
                        "properties": {},
                    })
                }
            }
            openai_tools.append(openai_tool)

        return openai_tools

    def get_tool_names(self) -> List[str]:
        """Get list of available tool names."""
        if not self._tools_cache:
            return []
        return [t["name"] for t in self._tools_cache]

    def get_status(self) -> Dict[str, Any]:
        """Get MCP client status."""
        return {
            "connected": self._connected,
            "server_command": self.server_command,
            "tools_available": len(self._tools_cache) if self._tools_cache else 0,
            "tool_names": self.get_tool_names(),
            "audit_stats": self.audit_logger.get_stats()
        }
