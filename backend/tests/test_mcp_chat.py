"""
Script to test the Grace OS MCP chat endpoint (/api/mcp/chat).
This demonstrates the full multi-turn tool-calling loop where the LLM
uses MCP tools to perform actions on the local file system.
"""

import requests
import json
import time

API_BASE_URL = "http://localhost:8000/api/mcp"

def test_mcp_chat(prompt: str):
    print(f"\n[USER] {prompt}")
    print("-" * 60)
    
    url = f"{API_BASE_URL}/chat"
    payload = {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3
    }
    
    try:
        start_time = time.time()
        print("Sending request to Grace API (this may take a moment if multiple tool calls are needed)...")
        response = requests.post(url, json=payload, timeout=120)
        duration = time.time() - start_time
        
        if response.status_code != 200:
            print(f"❌ Error {response.status_code}: {response.text}")
            return
            
        data = response.json()
        
        # Show tool calls made
        tool_calls = data.get("tool_calls_made", [])
        if tool_calls:
            print(f"\n[AI used {len(tool_calls)} tools]:")
            for i, tc in enumerate(tool_calls, 1):
                success_icon = "✅" if tc.get("success") else "❌"
                print(f"  {i}. {success_icon} {tc['tool']}({json.dumps(tc['arguments'])})")
        else:
            print("\n[AI used no tools]")
            
        print(f"\n[ASSISTANT] ({duration:.1f}s, turns: {data.get('turns')})")
        print(data.get("content"))
        
        return data
        
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to Grace API. Is the server running? (npm run dev/start.bat)")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("  Grace OS — MCP Chat Verification Test")
    print("=" * 60)
    
    # Test case 1: Simple file operation
    test_mcp_chat("Create a file named 'mcp_chat_test.md' in the current directory with a short poem about Grace OS, then read it back to verify.")
    
    print("\n" + "=" * 60)
    print("  Test script finished.")
    print("=" * 60)
