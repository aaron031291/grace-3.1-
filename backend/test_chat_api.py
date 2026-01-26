
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_chat_flow():
    print("Testing Chat Flow...")
    
    # 1. Create Chat
    print("\n1. Creating Chat...")
    try:
        response = requests.post(f"{BASE_URL}/chats", json={
            "title": "Test Chat",
            "model": "mistral:7b" 
        })
        if response.status_code != 200:
            print(f"FAILED to create chat: {response.status_code} {response.text}")
            # If mistral:7b is missing, it might fail with 400. Try requesting without model (default)
            print("Retrying with default model...")
            response = requests.post(f"{BASE_URL}/chats", json={"title": "Test Chat Default"})
            if response.status_code != 200:
                print(f"FAILED again: {response.text}")
                return
        
        chat = response.json()
        chat_id = chat['id']
        print(f"SUCCESS: Created chat {chat_id}")
        print(json.dumps(chat, indent=2))
        
    except Exception as e:
        print(f"EXCEPTION creating chat: {e}")
        return

    # 2. List Chats
    print("\n2. Listing Chats...")
    try:
        response = requests.get(f"{BASE_URL}/chats")
        if response.status_code != 200:
             print(f"FAILED to list chats: {response.status_code} {response.text}")
             return
        
        data = response.json()
        chats = data['chats']
        print(f"SUCCESS: Retrieved {len(chats)} chats")
        found = False
        for c in chats:
            if c['id'] == chat_id:
                found = True
                print(f"Found created chat in list: {c['id']}")
                break
        if not found:
            print(f"ERROR: Created chat {chat_id} not found in list!")
            
    except Exception as e:
        print(f"EXCEPTION listing chats: {e}")

    # 3. Get Chat Details
    print(f"\n3. Getting Chat {chat_id} details...")
    try:
        response = requests.get(f"{BASE_URL}/chats/{chat_id}")
        if response.status_code != 200:
             print(f"FAILED to get chat details: {response.status_code} {response.text}")
        else:
            print(f"SUCCESS: Got chat details for {chat_id}")
            # print(json.dumps(response.json(), indent=2))

    except Exception as e:
        print(f"EXCEPTION getting chat details: {e}")

    # 4. Get Chat Messages
    print(f"\n4. Getting Chat {chat_id} messages...")
    try:
        response = requests.get(f"{BASE_URL}/chats/{chat_id}/messages")
        if response.status_code != 200:
             print(f"FAILED to get messages: {response.status_code} {response.text}")
        else:
            print(f"SUCCESS: Got messages for {chat_id}")
            # print(json.dumps(response.json(), indent=2))
            
    except Exception as e:
        print(f"EXCEPTION getting messages: {e}")

if __name__ == "__main__":
    test_chat_flow()
