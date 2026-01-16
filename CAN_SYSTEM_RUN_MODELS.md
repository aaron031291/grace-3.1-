# ✅ Can GRACE Run These Models? - System Requirements & Verification

## Overview

**YES!** GRACE can run all these open-source models, but you need **Ollama** installed and running. Here's everything you need to know.

---

## 🔧 System Requirements

### 1. **Ollama Must Be Installed**

GRACE uses **Ollama** to run LLM models. Ollama is a free, open-source tool that runs models locally.

**Install Ollama:**
- **Windows/Mac/Linux:** Download from https://ollama.ai
- **Or via command line:**
  ```bash
  # Linux/Mac
  curl -fsSL https://ollama.ai/install.sh | sh
  
  # Windows - download installer from website
  ```

### 2. **Ollama Service Must Be Running**

GRACE connects to Ollama at `http://localhost:11434` (default).

**Check if Ollama is running:**
```bash
# Check if Ollama service is running
curl http://localhost:11434

# Or check process
# Windows: tasklist | findstr ollama
# Linux/Mac: ps aux | grep ollama
```

**Start Ollama:**
```bash
# Start Ollama service
ollama serve

# Or on Windows, it usually starts automatically after installation
```

### 3. **Models Must Be Pulled (Downloaded)**

Models need to be downloaded to your system first.

**Pull a model:**
```bash
ollama pull deepseek-coder-v2:16b-instruct
ollama pull deepseek-r1:70b
ollama pull codeqwen1.5:7b
```

---

## 💻 Hardware Requirements

### Minimum Requirements (Small Models)

- **RAM:** 8GB (for 7B models)
- **Storage:** 10GB free space
- **GPU:** Optional (CPU works, but slower)

### Recommended Requirements (Large Models)

- **RAM:** 32GB+ (for 70B models)
- **Storage:** 100GB+ free space
- **GPU:** NVIDIA GPU with 16GB+ VRAM (for fast inference)

### Model Size Guide

| Model Size | RAM Needed | VRAM Needed (GPU) | Storage |
|------------|------------|-------------------|---------|
| 1.3B       | 4GB        | 2GB               | 2GB     |
| 7B         | 8GB        | 6GB               | 4GB     |
| 13B        | 16GB       | 10GB              | 8GB     |
| 32B        | 32GB       | 20GB              | 20GB    |
| 70B        | 64GB       | 40GB              | 40GB    |

**Note:** Models can run on CPU, but GPU is much faster.

---

## ✅ How to Verify System Can Run Models

### Step 1: Check Ollama Installation

```bash
# Check if Ollama is installed
ollama --version

# Should output something like: ollama version is 0.x.x
```

### Step 2: Check Ollama Service

```bash
# Check if service is running
curl http://localhost:11434

# Or in Python:
python -c "import requests; print('OK' if requests.get('http://localhost:11434').status_code == 200 else 'NOT RUNNING')"
```

### Step 3: Check Installed Models

```bash
# List all installed models
ollama list

# Or via API:
curl http://localhost:11434/api/tags
```

### Step 4: Test Model Generation

```bash
# Test a small model
ollama run phi3:mini "Hello, can you respond?"

# If this works, your system can run models!
```

### Step 5: Check from GRACE

```bash
# Check available models via GRACE API
curl http://localhost:8000/llm/models

# Should return list of available models
```

---

## 🚀 Quick Start - Get Models Running

### 1. Install Ollama

```bash
# Visit https://ollama.ai and download for your OS
# Or use installer script (Linux/Mac):
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Start Ollama Service

```bash
# Start Ollama (usually auto-starts on Windows/Mac)
ollama serve

# Keep this running in a terminal
```

### 3. Pull Essential Models

```bash
# Start with small, fast models
ollama pull phi3:mini          # Very fast, 2GB
ollama pull codeqwen1.5:7b      # Fast code, 4GB
ollama pull deepseek-r1-distill:1.3b  # Fast reasoning, 2GB

# Then add larger models if you have resources
ollama pull deepseek-coder-v2:16b-instruct  # Best code, 10GB
ollama pull deepseek-r1:70b                  # Best reasoning, 40GB
```

### 4. Verify in GRACE

```bash
# Start GRACE
python backend/app.py

# Check models
curl http://localhost:8000/llm/models

# Test a query
curl -X POST http://localhost:8000/llm/task \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "task_type": "general"}'
```

---

## 🔍 How GRACE Connects to Models

### Connection Flow

```
GRACE Application
        ↓
OllamaClient (backend/ollama_client/client.py)
        ↓
HTTP Request to http://localhost:11434
        ↓
Ollama Service (running locally)
        ↓
Model Inference (on your hardware)
        ↓
Response back to GRACE
```

### Code Location

- **Ollama Client:** `backend/ollama_client/client.py`
- **Multi-LLM Client:** `backend/llm_orchestrator/multi_llm_client.py`
- **Settings:** `backend/settings.py` (OLLAMA_URL)

---

## ⚠️ Troubleshooting

### Problem: "Ollama not found"

**Solution:**
```bash
# Install Ollama from https://ollama.ai
# Or check if it's in PATH:
which ollama  # Linux/Mac
where ollama  # Windows
```

### Problem: "Connection refused" or "Cannot connect to Ollama"

**Solution:**
```bash
# Start Ollama service
ollama serve

# Check if it's running
curl http://localhost:11434
```

### Problem: "Model not found"

**Solution:**
```bash
# Pull the model first
ollama pull model-name:tag

# Example:
ollama pull deepseek-coder-v2:16b-instruct
```

### Problem: "Out of memory" or "Not enough RAM"

**Solution:**
- Use smaller models (7B instead of 70B)
- Close other applications
- Use CPU instead of GPU (slower but uses less VRAM)
- Add more RAM

### Problem: "Model too slow"

**Solution:**
- Use GPU instead of CPU
- Use smaller models
- Use quantized models (smaller, faster)
- Reduce context window size

---

## 📊 Model Selection by Hardware

### Low-End Hardware (8GB RAM, No GPU)

**Recommended Models:**
- `phi3:mini` (2GB) - Fastest
- `phi3:medium` (4GB) - Fast
- `codeqwen1.5:7b` (4GB) - Code tasks
- `deepseek-r1-distill:1.3b` (2GB) - Reasoning

### Mid-Range Hardware (16GB RAM, Optional GPU)

**Recommended Models:**
- `deepseek-coder-v2:16b-instruct` (10GB) - Best code
- `qwen2.5:14b-instruct` (8GB) - Balanced
- `mistral-small:22b` (12GB) - General purpose
- `llama3.1:8b-instruct` (5GB) - Fast general

### High-End Hardware (32GB+ RAM, GPU with 16GB+ VRAM)

**Recommended Models:**
- `deepseek-r1:70b` (40GB) - Best reasoning
- `qwen2.5:72b-instruct` (40GB) - Large context
- `deepseek-coder:33b-instruct` (20GB) - Large code
- `mixtral:8x7b` (26GB) - MoE model

---

## ✅ Verification Checklist

- [ ] Ollama is installed (`ollama --version`)
- [ ] Ollama service is running (`curl http://localhost:11434`)
- [ ] At least one model is pulled (`ollama list`)
- [ ] Test model works (`ollama run phi3:mini "test"`)
- [ ] GRACE can see models (`curl http://localhost:8000/llm/models`)
- [ ] GRACE can generate responses (test API call)

---

## 🎯 Next Steps

1. **Install Ollama** if not already installed
2. **Start Ollama service** (`ollama serve`)
3. **Pull a test model** (`ollama pull phi3:mini`)
4. **Verify in GRACE** (check `/llm/models` endpoint)
5. **Pull more models** as needed based on your hardware

---

## 📝 Summary

**YES, GRACE can run all these models!** You just need:

1. ✅ **Ollama installed** - Free, open-source
2. ✅ **Ollama service running** - Usually auto-starts
3. ✅ **Models pulled** - Download with `ollama pull`
4. ✅ **Enough hardware** - RAM/VRAM for model size

The system automatically:
- ✅ Discovers installed models
- ✅ Selects best model for each task
- ✅ Handles model switching
- ✅ Manages connections to Ollama

**All models in the registry are compatible with Ollama and will work once pulled!**

---

**Version:** 1.0  
**Date:** 2026-01-15  
**Status:** ✅ System Can Run All Models (with Ollama)
