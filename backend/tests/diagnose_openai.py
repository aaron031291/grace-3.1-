
import requests
import os
from dotenv import load_dotenv

load_dotenv("backend/.env")

api_key = os.getenv("LLM_API_KEY")
model = os.getenv("LLM_MODEL", "gpt-4o")

print(f"Testing OpenAI with model: {model}")
print(f"API Key present: {bool(api_key)}")

url = "https://api.openai.com/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Say hello"}],
    "max_tokens": 5
}

try:
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"Response Status: {response.status_code}")
    print(f"Response Content: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Also check /models
print("\nChecking /models endpoint:")
try:
    response = requests.get("https://api.openai.com/v1/models", headers=headers, timeout=10)
    print(f"Response Status: {response.status_code}")
    if response.status_code == 200:
        models = response.json().get('data', [])
        print(f"Found {len(models)} models")
        print(f"Is {model} in models? {any(m['id'] == model for m in models)}")
    else:
        print(f"Response Content: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
