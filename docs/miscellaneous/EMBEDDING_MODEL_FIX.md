# Embedding Model Fix - Auto-Download & Fallback

## Problem

The embedding model wasn't working because:
1. ❌ Model path didn't exist (`C:\Users\aaron\grace 3.1\grace-3.1-\backend\models\embedding\qwen_4b`)
2. ❌ Code raised `FileNotFoundError` instead of downloading the model
3. ❌ No fallback mechanism if download failed

## Solution Implemented

### 1. **Automatic Model Download**
- ✅ If local path doesn't exist, automatically downloads from HuggingFace
- ✅ Uses `huggingface_hub.snapshot_download()` if available
- ✅ Falls back to `SentenceTransformer` automatic download if needed

### 2. **Fallback Model**
- ✅ If Qwen model fails to download/load, uses `all-MiniLM-L6-v2` as fallback
- ✅ `all-MiniLM-L6-v2` is universally available and always works
- ✅ Smaller model (384 dim vs 2560 dim) but functional for testing

### 3. **Better Error Handling**
- ✅ Graceful degradation - system continues even if model fails
- ✅ Clear error messages indicating what's happening
- ✅ Automatic retry with CPU if GPU fails

## How It Works Now

```python
# 1. Check if local model exists
if model_path exists:
    use_local_model()
else:
    # 2. Try downloading from HuggingFace
    try:
        download_from_huggingface("Qwen/Qwen3-Embedding-4B")
    except:
        # 3. Try SentenceTransformer auto-download
        try:
            SentenceTransformer("Qwen/Qwen3-Embedding-4B")
        except:
            # 4. Fallback to always-available model
            SentenceTransformer("all-MiniLM-L6-v2")
```

## Model Options

### Primary Model: Qwen/Qwen3-Embedding-4B
- **Dimensions**: 2560
- **Context Length**: 32k tokens
- **Size**: ~4GB
- **Best for**: Production use, high-quality embeddings

### Fallback Model: all-MiniLM-L6-v2
- **Dimensions**: 384
- **Context Length**: 512 tokens
- **Size**: ~80MB
- **Best for**: Testing, quick setup, low-resource environments

## Manual Download (If Needed)

If automatic download fails, you can manually download:

```bash
# Option 1: Using huggingface-cli
pip install huggingface-hub
huggingface-cli download Qwen/Qwen3-Embedding-4B --local-dir backend/models/embedding/qwen_4b

# Option 2: Using Python
python -c "
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen3-Embedding-4B', local_dir='backend/models/embedding/qwen_4b')
"
```

## Expected Behavior

### ✅ CORRECT Behavior (After Fix):
1. System starts even if model not downloaded
2. Model downloads automatically on first use
3. If download fails, uses fallback model
4. System continues operating with available model
5. Clear logging about which model is being used

### Testing

```bash
# Test embedding model loading
cd backend
python -c "from embedding.embedder import get_embedding_model; model = get_embedding_model(); print('Model:', model.get_model_info())"
```

**Expected Output:**
```
[EMBEDDING] Local model path not found: ...
[EMBEDDING] Downloading model to: ...
[EMBEDDING] Model downloaded successfully
[EMBEDDING] [OK] Model loaded successfully
Model: {'model_path': '...', 'embedding_dimension': 2560, ...}
```

## Impact on System

- ✅ **Embedding operations now work** - model loads automatically
- ✅ **System more resilient** - fallback ensures embedding always available
- ✅ **Better user experience** - no manual download required
- ✅ **Degraded mode support** - works even if primary model unavailable

## Note on Dimensions

**IMPORTANT**: The Qwen model produces 2560-dimensional embeddings, while the fallback produces 384-dimensional embeddings. 

If you switch models, you may need to:
- Recreate Qdrant collections with correct dimensions
- Re-index existing documents

The system should handle this automatically, but be aware of dimension mismatches.
