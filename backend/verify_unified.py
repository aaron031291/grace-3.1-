"""
Verify the Unified Orchestrator — confirms builtin + MCP tools merge correctly.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def main():
    print("=" * 60)
    print("  Grace OS — Unified Orchestrator Verification")
    print("=" * 60)

    # Test 1: Import builtin tools
    print("\n[1/5] Testing builtin tools import...")
    try:
        from grace_mcp.builtin_tools import get_builtin_tools
        tools = get_builtin_tools(enable_rag=True, enable_web=True)
        print(f"  ✅ {len(tools)} builtin tools defined:")
        for t in tools:
            avail = "✅" if t.is_available() else "⚠️ (env missing)"
            print(f"     - {t.name}: {avail}")
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return

    # Test 2: Initialize unified orchestrator
    print("\n[2/5] Initializing unified orchestrator...")
    try:
        from grace_mcp.orchestrator import MCPOrchestrator
        orch = MCPOrchestrator(enable_rag=True, enable_web=True)
        success = await orch.initialize()
        if success:
            status = orch.get_status()
            print(f"  ✅ Orchestrator ready!")
            print(f"     Total tools: {status['tools_total']}")
            print(f"     MCP tools:   {status['tools_mcp']}")
            print(f"     Builtin:     {status['tools_builtin']}")
        else:
            print("  ❌ Initialization failed")
            return
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return

    # Test 3: Verify builtin tools are in the OpenAI format list
    print("\n[3/5] Checking OpenAI function format includes builtins...")
    tool_names = [t["function"]["name"] for t in orch._tools_openai_format]
    builtin_names = ["rag_search", "web_search", "web_fetch"]
    for name in builtin_names:
        if name in tool_names:
            print(f"  ✅ {name} found in tool list")
        else:
            if name in ["web_search"] and name not in orch._builtin_tools:
                print(f"  ⚠️ {name} skipped (SERPAPI_KEY not set)")
            else:
                print(f"  ❌ {name} MISSING from tool list")

    # Test 4: Test RAG search tool directly
    print("\n[4/5] Testing rag_search builtin tool...")
    try:
        if "rag_search" in orch._builtin_tools:
            result = await orch._builtin_tools["rag_search"].handler(
                {"query": "file ingestion", "limit": 2}
            )
            print(f"  ✅ rag_search succeeded: {result['success']}")
            preview = result["content"][:150].replace("\n", " ")
            print(f"     Preview: {preview}...")
        else:
            print("  ⚠️ rag_search not registered")
    except Exception as e:
        print(f"  ❌ rag_search error: {e}")

    # Test 5: Test MCP tool still works through orchestrator
    print("\n[5/5] Testing MCP tool (list_directory) through orchestrator...")
    try:
        result = await orch.mcp_client.call_tool(
            "list_directory",
            {"path": "."},
            calling_layer="verification"
        )
        if result["success"]:
            lines = result["content"].split("\n")[:3]
            print(f"  ✅ list_directory succeeded ({result.get('duration_ms', 0):.0f}ms)")
            for line in lines:
                print(f"     {line}")
        else:
            print(f"  ❌ list_directory failed: {result.get('error')}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Cleanup
    await orch.shutdown()

    print("\n" + "=" * 60)
    print("  ✅ Unified Orchestrator verification complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
