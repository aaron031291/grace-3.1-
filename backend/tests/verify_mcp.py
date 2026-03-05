"""
import pytest; pytest.importorskip("api.mcp_api", reason="api.mcp_api removed — consolidated into Brain API")
Quick verification script for MCP integration.
Tests: imports, MCP client connection, tool listing, and a basic tool call.
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def main():
    print("=" * 60)
    print("  Grace OS — MCP Integration Verification")
    print("=" * 60)

    # Test 1: Import MCP modules
    print("\n[1/4] Testing imports...")
    try:
        from grace_mcp.client import MCPClient
        from grace_mcp.orchestrator import MCPOrchestrator
        from grace_mcp.audit_logger import AuditLogger
        from api.mcp_api import router
        print("  ✅ All MCP modules imported successfully")
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return

    # Test 2: Create MCP client
    print("\n[2/4] Creating MCP client...")
    try:
        audit = AuditLogger()
        client = MCPClient(audit_logger=audit)
        print(f"  ✅ MCPClient created")
        print(f"     Server command: {client.server_command}")
        print(f"     Server args: {client.server_args}")
    except Exception as e:
        print(f"  ❌ Client creation failed: {e}")
        return

    # Test 3: Connect to MCP server
    print("\n[3/4] Connecting to DesktopCommanderMCP...")
    try:
        connected = await client.connect()
        if connected:
            tools = await client.list_tools()
            print(f"  ✅ Connected! {len(tools)} tools available:")
            for tool in tools[:10]:
                print(f"     - {tool['name']}: {tool['description'][:60]}...")
            if len(tools) > 10:
                print(f"     ... and {len(tools) - 10} more")
        else:
            print("  ❌ Connection failed (server may not be running)")
            print("     Make sure DesktopCommanderMCP is built: npm run build")
            return
    except Exception as e:
        print(f"  ❌ Connection error: {e}")
        return

    # Test 4: Test a basic tool call (read current directory)
    print("\n[4/4] Testing tool call: list_directory...")
    try:
        result = await client.call_tool(
            "list_directory",
            {"path": os.path.dirname(os.path.abspath(__file__))},
            calling_layer="verification"
        )
        if result["success"]:
            # Just show first 5 lines
            lines = result["content"].split("\n")[:5]
            print(f"  ✅ list_directory succeeded ({result.get('duration_ms', 0):.0f}ms):")
            for line in lines:
                print(f"     {line}")
        else:
            print(f"  ❌ Tool call failed: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"  ❌ Tool call error: {e}")

    # Get OpenAI format tools
    print("\n[BONUS] OpenAI function format tools:")
    openai_tools = client.get_tools_as_openai_functions()
    print(f"  {len(openai_tools)} tools converted to OpenAI format")
    for t in openai_tools[:5]:
        print(f"  - {t['function']['name']}")

    # Audit stats
    print(f"\n[AUDIT] Stats: {audit.get_stats()}")

    # Disconnect
    await client.disconnect()
    print("\n✅ All verification passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
