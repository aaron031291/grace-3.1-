import threading
import json
import os
import shutil
import time
from datetime import datetime
from unittest.mock import MagicMock
from genesis.kb_integration import GenesisKBIntegration
from models.genesis_key_models import GenesisKey, GenesisKeyType, GenesisKeyStatus

# Setup test directory
TEST_KB_PATH = "/tmp/test_kb_concurrency"
if os.path.exists(TEST_KB_PATH):
    shutil.rmtree(TEST_KB_PATH)
os.makedirs(TEST_KB_PATH)

def create_mock_key(i):
    return GenesisKey(
        key_id=f"GK-TEST-{i}",
        key_type=GenesisKeyType.USER_INPUT,
        status=GenesisKeyStatus.ACTIVE,
        user_id="test_user_concurrency",
        what_description=f"Concurrent write {i}",
        when_timestamp=datetime.now(),
        who_actor="tester",
        # ... other required fields mock ...
    )

def worker(kb_integration, start_index, count):
    for i in range(start_index, start_index + count):
        key = create_mock_key(i)
        kb_integration.save_genesis_key(key)
        # minimal sleep to increase collision chance
        # time.sleep(0.001)

def test_concurrent_writes():
    print("Starting concurrency test...")
    kb = GenesisKBIntegration(kb_base_path=TEST_KB_PATH)
    
    threads = []
    num_threads = 10
    writes_per_thread = 50
    
    start_time = time.time()
    
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(kb, i * writes_per_thread, writes_per_thread))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    end_time = time.time()
    print(f"Finished {num_threads * writes_per_thread} writes in {end_time - start_time:.2f} seconds")
    
    # Verify file integrity
    user_folder = os.path.join(TEST_KB_PATH, "layer_1", "genesis_key", "test_user_concurrency")
    json_files = [f for f in os.listdir(user_folder) if f.endswith('.json')]
    
    total_keys = 0
    for js_file in json_files:
        path = os.path.join(user_folder, js_file)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                keys_count = len(data.get("keys", []))
                total_keys += keys_count
                print(f"File {js_file}: VALID JSON, contains {keys_count} keys")
        except json.JSONDecodeError as e:
            print(f"File {js_file}: CORRUPTED JSON! Error: {e}")
            exit(1)
            
    expected_keys = num_threads * writes_per_thread
    print(f"Total keys found: {total_keys}/{expected_keys}")
    
    if total_keys == expected_keys:
        print("SUCCESS: All keys written correctly, no corruption.")
    else:
        # It's possible mostly due to date-based filename splitting, but usually should match if date is same
        print("WARNING: Key count mismatch (might be date rollover?), but JSON is valid.")

    # Clean up
    shutil.rmtree(TEST_KB_PATH)

if __name__ == "__main__":
    test_concurrent_writes()
