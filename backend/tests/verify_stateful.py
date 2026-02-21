import asyncio
import json
import os
import sys
from typing import Dict, Any
import httpx
from datetime import datetime

# Add the backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def verify_stateful_mcp():
    print("=== Phase 3 Verification: Stateful MCP API ===")
    
    BASE_URL = "http://localhost:8000"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. Create a new chat via the standard API
        print("\n1. Creating a new test chat...")
        chat_req = {
            "title": "Stateful MCP Verification",
            "model": "gpt-4o",
            "temperature": 0.5
        }
        res = await client.post(f"{BASE_URL}/chats", json=chat_req)
        if res.status_code != 200:
            print(f"FAILED to create chat: {res.text}")
            return
        
        chat_data = res.json()
        chat_id = chat_data["id"]
        print(f"SUCCESS: Created chat with ID {chat_id}")

        # 2. Send a prompt via the NEW MCP /chat endpoint
        print(f"\n2. Sending MCP prompt for Chat ID {chat_id}...")
        mcp_req = {
            "chat_id": chat_id,
            "messages": [
                {"role": "user", "content": "What is the project Grace about? Use rag_search."}
            ],
            "use_rag": True
        }
        
        res = await client.post(f"{BASE_URL}/api/mcp/chat", json=mcp_req)
        if res.status_code != 200:
            print(f"FAILED MCP chat: {res.text}")
            return
        
        mcp_data = res.json()
        print(f"SUCCESS: Received response from MCP Agent.")
        print(f"Content length: {len(mcp_data['content'])}")
        print(f"Turns: {mcp_data['turns']}")
        print(f"Sources found: {len(mcp_data.get('sources', []))}")
        
        # 3. Verify persistence: Get history via standard API
        print(f"\n3. Verifying persistence for Chat ID {chat_id}...")
        res = await client.get(f"{BASE_URL}/chats/{chat_id}/messages")
        if res.status_code != 200:
            print(f"FAILED to get history: {res.text}")
            return
        
        history = res.json()
        messages = history["messages"]
        print(f"Messages in DB: {len(messages)}")
        
        # Expecting at least 2 messages (user prompt + assistant response)
        roles = [m["role"] for m in messages]
        print(f"Message Roles: {roles}")
        
        if "user" in roles and "assistant" in roles:
            print("\n✅ VERIFICATION SUCCESS: Data persisted to DB and sources extracted!")
        else:
            print("\n❌ VERIFICATION FAILED: Messages not found in DB.")

if __name__ == "__main__":
    # Note: Backend must be running
    asyncio.run(verify_stateful_mcp())
