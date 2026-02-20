"""
Grace OS — MCP (Model Context Protocol) Integration Module.

This module provides:
- MCPClient: Connects to MCP servers (DesktopCommanderMCP) via stdio transport
- MCPOrchestrator: Manages multi-turn tool-calling loops between LLM and MCP
- AuditLogger: Logs every tool call for observability and trust scoring
"""

from grace_mcp.client import MCPClient
from grace_mcp.orchestrator import MCPOrchestrator
from grace_mcp.audit_logger import AuditLogger

__all__ = ["MCPClient", "MCPOrchestrator", "AuditLogger"]
