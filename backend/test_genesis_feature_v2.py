import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_genesis_feature():
    print("Testing Genesis Key Feature...")

    # Check if server is running
    try:
        requests.get(f"{BASE_URL}/health")
    except requests.exceptions.ConnectionError:
        print("Server is not running on http://localhost:8000. Please start the backend server first.")
        return

    # 1. Create User
    print("\n[1] Creating User Profile...")
    user_payload = {
        "username": "test_user_genesis",
        "email": "test@genesis.com"
    }
    user_id = None
    try:
        response = requests.post(f"{BASE_URL}/genesis/users", json=user_payload)
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data["user_id"]
            print(f"User created: {user_id}")
        else:
            print(f"User creation failed (status {response.status_code}): {response.text}")
            # Try to fetch if it exists? or just proceed
            user_id = "test_user_fallback"
    except Exception as e:
        print(f"Error creating user: {e}")
        user_id = "test_user_fallback"

    # 2. Create Genesis Key
    print("\n[2] Creating Genesis Key...")
    key_payload = {
        "key_type": "user_input",
        "what_description": "Testing genesis key creation",
        "who_actor": "test_script",
        "where_location": "test_genesis_feature_v2.py",
        "why_reason": "Validation of feature",
        "how_method": "API Call",
        "user_id": user_id,
        "tags": ["test", "genesis"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/genesis/keys", json=key_payload)
        if response.status_code != 200:
            print(f"Failed to create key: {response.status_code} - {response.text}")
            return
        
        key_data = response.json()
        key_id = key_data["key_id"]
        print(f"Genesis Key Created: {key_id}")
        # print(json.dumps(key_data, indent=2))
        
        # Verify key data
        assert key_data["what_description"] == key_payload["what_description"]
        assert key_data["key_type"] == key_payload["key_type"]
        print("[PASS] Key creation validated")

        # 3. Get Key
        print(f"\n[3] Retrieving Key {key_id}...")
        response = requests.get(f"{BASE_URL}/genesis/keys/{key_id}")
        if response.status_code == 200:
            retrieved_key = response.json()
            assert retrieved_key["key_id"] == key_id
            print("[PASS] Key retrieval validated")
        else:
            print(f"Failed to retrieve key: {response.status_code}")

        # 4. List Keys
        print("\n[4] Listing Keys...")
        response = requests.get(f"{BASE_URL}/genesis/keys?limit=5")
        if response.status_code == 200:
            keys = response.json()
            print(f"Retrieved {len(keys)} keys")
            found = False
            for k in keys:
                if k["key_id"] == key_id:
                    found = True
                    break
            if found:
                print("[PASS] Newly created key found in list")
            else:
                print("[WARN] Newly created key NOT found in recent list (might be pagination or order)")
        else:
            print(f"Failed to list keys: {response.status_code}")

        # 5. Stats
        print("\n[5] Getting Stats...")
        response = requests.get(f"{BASE_URL}/genesis/stats")
        if response.status_code == 200:
            print(json.dumps(response.json(), indent=2))
            print("[PASS] Stats retrieved")
        else:
            print(f"Failed to get stats: {response.status_code}")
            
    except Exception as e:
        print(f"Test failed with exception: {e}")

if __name__ == "__main__":
    test_genesis_feature()
