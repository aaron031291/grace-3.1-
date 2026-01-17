#!/usr/bin/env python3
"""
Quick verification script to check if GRACE can run LLM models.

Run this to verify:
1. Ollama is installed
2. Ollama service is running
3. Models are available
4. GRACE can connect to models
"""

import sys
import requests
import subprocess
from pathlib import Path

def check_ollama_installed():
    """Check if Ollama is installed."""
    print("🔍 Checking if Ollama is installed...")
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✅ Ollama is installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ Ollama is not installed")
            return False
    except FileNotFoundError:
        print("❌ Ollama is not installed")
        print("   Install from: https://ollama.ai")
        return False
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")
        return False

def check_ollama_running():
    """Check if Ollama service is running."""
    print("\n🔍 Checking if Ollama service is running...")
    try:
        response = requests.get("http://localhost:11434", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama service is running")
            return True
        else:
            print(f"❌ Ollama service returned status {response.status_code}")
            return False
    except requests.ConnectionError:
        print("❌ Ollama service is NOT running")
        print("   Start it with: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Error connecting to Ollama: {e}")
        return False

def check_installed_models():
    """Check what models are installed."""
    print("\n🔍 Checking installed models...")
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            if models:
                print(f"✅ Found {len(models)} installed model(s):")
                for model in models[:10]:  # Show first 10
                    name = model.get("name", "unknown")
                    size = model.get("size", 0)
                    size_gb = size / (1024**3)
                    print(f"   - {name} ({size_gb:.1f} GB)")
                if len(models) > 10:
                    print(f"   ... and {len(models) - 10} more")
                return True, models
            else:
                print("⚠️  No models installed")
                print("   Install models with: ollama pull <model-name>")
                return False, []
        else:
            print(f"❌ Failed to get models: status {response.status_code}")
            return False, []
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        return False, []

def test_model_generation():
    """Test if a model can generate responses."""
    print("\n🔍 Testing model generation...")
    try:
        # Try to find a small model first
        response = requests.get("http://localhost:11434/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            
            if not models:
                print("⚠️  No models available to test")
                return False
            
            # Try smallest model first
            test_model = models[0].get("name", "")
            
            print(f"   Testing with: {test_model}")
            
            payload = {
                "model": test_model,
                "prompt": "Say 'Hello' if you can read this.",
                "stream": False
            }
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("response"):
                    print(f"✅ Model generation works!")
                    print(f"   Response: {result.get('response', '')[:50]}...")
                    return True
                else:
                    print("❌ Model returned empty response")
                    return False
            else:
                print(f"❌ Model generation failed: status {response.status_code}")
                return False
        else:
            print("❌ Cannot test - Ollama not accessible")
            return False
    except Exception as e:
        print(f"❌ Error testing model: {e}")
        return False

def check_grace_connection():
    """Check if GRACE can connect to models."""
    print("\n🔍 Checking GRACE connection to models...")
    try:
        response = requests.get("http://localhost:8000/llm/models", timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            if models:
                print(f"✅ GRACE can see {len(models)} model(s)")
                return True
            else:
                print("⚠️  GRACE is running but no models available")
                return False
        else:
            print("⚠️  GRACE API not accessible (is GRACE running?)")
            print("   Start GRACE with: python backend/app.py")
            return False
    except requests.ConnectionError:
        print("⚠️  GRACE is not running")
        print("   Start GRACE with: python backend/app.py")
        return False
    except Exception as e:
        print(f"⚠️  Error checking GRACE: {e}")
        return False

def main():
    """Run all checks."""
    print("=" * 60)
    print("GRACE LLM Model Verification")
    print("=" * 60)
    
    results = {
        "ollama_installed": check_ollama_installed(),
        "ollama_running": False,
        "models_installed": False,
        "model_generation": False,
        "grace_connection": False
    }
    
    if not results["ollama_installed"]:
        print("\n" + "=" * 60)
        print("❌ CANNOT RUN MODELS - Ollama not installed")
        print("=" * 60)
        print("\n📥 Install Ollama from: https://ollama.ai")
        return 1
    
    results["ollama_running"] = check_ollama_running()
    
    if not results["ollama_running"]:
        print("\n" + "=" * 60)
        print("❌ CANNOT RUN MODELS - Ollama service not running")
        print("=" * 60)
        print("\n🚀 Start Ollama with: ollama serve")
        return 1
    
    models_installed, models = check_installed_models()
    results["models_installed"] = models_installed
    
    if models_installed:
        results["model_generation"] = test_model_generation()
    
    results["grace_connection"] = check_grace_connection()
    
    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_checks = [
        ("Ollama Installed", results["ollama_installed"]),
        ("Ollama Running", results["ollama_running"]),
        ("Models Installed", results["models_installed"]),
        ("Model Generation", results["model_generation"]),
        ("GRACE Connection", results["grace_connection"]),
    ]
    
    for check_name, check_result in all_checks:
        status = "✅" if check_result else "❌"
        print(f"{status} {check_name}")
    
    # Final verdict
    if all([results["ollama_installed"], results["ollama_running"], results["models_installed"]]):
        print("\n" + "=" * 60)
        print("✅ SYSTEM CAN RUN MODELS!")
        print("=" * 60)
        
        if not results["model_generation"]:
            print("\n⚠️  Models are installed but generation test failed")
            print("   Try: ollama run <model-name> 'test'")
        
        if not results["grace_connection"]:
            print("\n⚠️  GRACE is not running or cannot connect")
            print("   Start GRACE with: python backend/app.py")
        
        print("\n📚 Recommended next steps:")
        print("   1. Pull more models: ollama pull <model-name>")
        print("   2. Start GRACE: python backend/app.py")
        print("   3. Test via API: curl http://localhost:8000/llm/models")
        
        return 0
    else:
        print("\n" + "=" * 60)
        print("❌ SYSTEM CANNOT RUN MODELS YET")
        print("=" * 60)
        
        print("\n📋 Required steps:")
        if not results["ollama_installed"]:
            print("   1. Install Ollama: https://ollama.ai")
        if not results["ollama_running"]:
            print("   2. Start Ollama: ollama serve")
        if not results["models_installed"]:
            print("   3. Pull a model: ollama pull phi3:mini")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
