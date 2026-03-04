# Model Switching Guide

This document explains how to switch between embedding models for different environments.

## Quick Switch

### For Laptop Testing (Lightweight)
```bash
# In backend/.env
EMBEDDING_DEFAULT=all-MiniLM-L6-v2
EMBEDDING_MODEL_PATH=./models/embedding/all-MiniLM-L6-v2
SKIP_EMBEDDING_LOAD=false
```

### For Production/Deployment (Qwen-4B)
```bash
# In backend/.env
EMBEDDING_DEFAULT=qwen_4b
EMBEDDING_MODEL_PATH=./models/embedding/qwen_4b
SKIP_EMBEDDING_LOAD=false
```

## Model Comparison

| Model | Size | RAM | Dimensions | Quality | Use Case |
|-------|------|-----|------------|---------|----------|
| **Qwen-4B** | ~8 GB | ~10 GB | 2560 | Excellent | Production |
| **all-MiniLM-L6-v2** | ~90 MB | ~500 MB | 384 | Good | Laptop Testing |

## Setup Instructions

### 1. Download Lightweight Model

```bash
cd backend
source venv/bin/activate
python download_lightweight_model.py
```

### 2. Update .env File

Edit `backend/.env`:
```bash
EMBEDDING_DEFAULT=all-MiniLM-L6-v2
EMBEDDING_MODEL_PATH=./models/embedding/all-MiniLM-L6-v2
SKIP_EMBEDDING_LOAD=false
```

### 3. Restart Backend

```bash
# Stop current backend (Ctrl+C)
python app.py
```

## Switching Back to Qwen-4B

Just edit `.env` and change back:
```bash
EMBEDDING_DEFAULT=qwen_4b
EMBEDDING_MODEL_PATH=./models/embedding/qwen_4b
```

Then restart the backend.

## No Code Changes Needed!

The beauty of this approach is that **no code changes are required**. Grace's architecture reads the model configuration from `.env`, so you can switch models by just changing the configuration file.

## Verification

After switching models, check the backend logs on startup:
```
[STARTUP] Pre-initializing embedding model...
[STARTUP] ✓ Embedding model loaded and ready
```

You should see the model load successfully.
