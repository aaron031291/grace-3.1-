"""
Demo: Unified Agent Coordination — Grace OS

This script verifies the "Unified" part of the orchestrator. 
It sends a complex request to the LLM that requires using ALL tool categories:
1. web_search (for current info) 
2. rag_search (for local knowledge)
3. write_file (MCP tool to save result)

Requirements:
- .env with LLM_API_KEY, SERPAPI_KEY
- DesktopCommanderMCP built
"""

import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Load env and setup paths
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging to be clean for the demo
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("UnifiedDemo")

async def run_demo():
    print("\n" + "="*80)
    print("🚀 GRACE OS: UNIFIED AGENT DEMO")
    print("="*80)
    
    from grace_mcp.orchestrator import MCPOrchestrator
    
    # 1. Initialize Orchestrator
    logger.info("\n[1/3] Initializing Unified Orchestrator...")
    orch = MCPOrchestrator(enable_rag=True, enable_web=True)
    success = await orch.initialize()
    
    if not success:
        logger.error("❌ Failed to initialize orchestrator. Check DesktopCommanderMCP build.")
        return

    status = orch.get_status()
    logger.info(f"✅ Ready with {status['tools_total']} tools!")
    logger.info(f"   Builtins: {status['tools_builtin']}")
    logger.info(f"   MCP Tools: {status['tools_mcp']} (File system, Terminal, etc.)")

    # 2. Define the "Master Query"
    # This query specifically targets all 3 capabilities
    query = (
        "Project: Python Version Research\n"
        "1. Search the web for the current latest stable Python version.\n"
        "2. Search the Grace knowledge base for 'deployment' to see our preferred python flags.\n"
        "3. Create a file named 'mcp_demo_report.txt' with a summary of both.\n"
        "4. Output 'DEMO COMPLETE' when done."
    )

    print("\n" + "-"*80)
    print(f"USER QUERY:\n{query}")
    print("-"*80)

    # 3. Execute Chat Loop
    print("\n[2/3] Executing multi-turn reasoning loop...")
    
    messages = [{"role": "user", "content": query}]
    
    # Callback to show tool usage in real-time
    def on_tool(name, args):
        print(f"\n   🔧 [AGENT CALLS TOOL]: {name}")
        for k, v in args.items():
            val = str(v)[:100] + "..." if len(str(v)) > 100 else v
            print(f"      {k}: {val}")

    try:
        start_time = asyncio.get_event_loop().time()
        result = await orch.chat(
            messages=messages,
            on_tool_call=on_tool
        )
        duration = asyncio.get_event_loop().time() - start_time

        print("\n" + "-"*80)
        print(f"AI RESPONSE ({result['turns']} turns, {duration:.1f}s):\n")
        print(result["content"])
        print("-"*80)

        # 4. Verify the file was actually created via MCP
        print("\n[3/3] Verifying output file 'mcp_demo_report.txt' exists...")
        if os.path.exists("mcp_demo_report.txt"):
            with open("mcp_demo_report.txt", "r") as f:
                content = f.read()
                print(f"  ✅ File found! Content preview ({len(content)} bytes):")
                print(f"     {content[:150]}...")
            
            # Clean up
            # os.remove("mcp_demo_report.txt")
            # print("  ✅ Cleaned up temp file.")
        else:
            print("  ❌ File 'mcp_demo_report.txt' was not found.")

    except Exception as e:
        logger.error(f"❌ Demo execution failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await orch.shutdown()

    print("\n" + "="*80)
    print("✨ DEMO COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(run_demo())
