# Hardware Specifications Audit Report

## Issues Found

### 🔴 CRITICAL: Model Sizes Exceed Constraints

**Problem:** Model registry includes models that exceed your 24GB max_model_size_gb constraint.

1. **`deepseek-r1-70b` (70B model)**
   - Estimated size: ~40-45GB (quantized) or ~140GB (unquantized)
   - **EXCEEDS** 24GB limit by 16-21GB (quantized) or 116GB (unquantized)
   - Status: ❌ **OUT OF SPEC**

2. **`qwen2.5-32b` (32B model)**
   - Estimated size: ~20-22GB (quantized)
   - Within 24GB limit but very close
   - Status: ⚠️ **AT LIMIT** (should be monitored)

3. **`deepseek-coder-v2-16b` (16B model)**
   - Estimated size: ~10-12GB
   - Status: ✅ **WITHIN SPEC**

### 🟡 WARNING: Batch Sizes Higher Than Recommended

**Problem:** Several components use batch sizes higher than your recommended batch_size: 4.

1. **Embedding Model**
   - Default: `batch_size=32`
   - Recommended: `batch_size=4`
   - Location: `backend/embedding/embedder.py:170`
   - Status: ⚠️ **8x HIGHER** than recommended

2. **Ingestion Service**
   - Default: `batch_size=16` with fallback to 4
   - Recommended: `batch_size=4`
   - Location: `backend/ingestion/service.py`
   - Status: ⚠️ **4x HIGHER** than recommended

3. **Adaptive File Processor**
   - Uses: `batch_size=32`, `batch_size=64` in some cases
   - Recommended: `batch_size=4`
   - Location: `backend/file_manager/adaptive_file_processor.py`
   - Status: ⚠️ **8-16x HIGHER** than recommended

### 🟡 WARNING: Concurrent Requests May Exceed Limit

**Problem:** Multi-LLM client allows up to 10 concurrent requests, which could load multiple models simultaneously.

1. **Multi-LLM Client**
   - `max_concurrent_requests: int = 10`
   - Your constraint: `max_concurrent_models: 2`
   - Location: `backend/llm_orchestrator/multi_llm_client.py:408`
   - Status: ⚠️ **5x HIGHER** than recommended

### ✅ GOOD: Embedding Model Size

- **Qwen3-Embedding-4B**: ~4-6GB
- Status: ✅ **WITHIN SPEC**

## Recommendations

### Immediate Actions

1. **Remove or comment out `deepseek-r1-70b`** from model registry
   - This model is too large for your hardware
   - Consider using `deepseek-r1-distill-1.3b` instead (much smaller, still good reasoning)

2. **Reduce default batch sizes** to match your specs
   - Embedding: 32 → 4
   - Ingestion: 16 → 4
   - File processor: 32/64 → 4

3. **Limit concurrent requests** to 2
   - Multi-LLM client: 10 → 2

4. **Monitor `qwen2.5-32b`** usage
   - Keep it but be aware it's at the limit
   - Consider using smaller alternatives if issues arise

### Optional Improvements

1. **Add automatic batch size adjustment** based on available VRAM
2. **Add model size validation** before loading
3. **Add concurrent model limit enforcement**

## Fixes Applied

### ✅ Fixed: Model Registry
- **Commented out `deepseek-r1-70b`** - Model too large (~40GB exceeds 24GB limit)
- **Kept `qwen2.5-32b`** - Within limit but monitored
- **Note added** explaining why 70B model is disabled

### ✅ Fixed: Batch Sizes
- **Embedding model**: 32 → 4 (8x reduction)
- **Ingestion service**: 32 → 4 (8x reduction)
- **Adaptive file processor**: 32/16/64 → 4 (all cases)

### ✅ Fixed: Concurrent Requests
- **Multi-LLM client**: 10 → 2 (5x reduction)
- Now respects `max_concurrent_models: 2` constraint

## Summary

| Component | Before | After | Status |
|-----------|--------|-------|--------|
| deepseek-r1-70b | ~40GB | **DISABLED** | ✅ **FIXED** |
| qwen2.5-32b | ~20GB | ~20GB | ⚠️ **AT LIMIT** (monitored) |
| Embedding batch | 32 | **4** | ✅ **FIXED** |
| Ingestion batch | 32 | **4** | ✅ **FIXED** |
| File processor batch | 32/16/64 | **4** | ✅ **FIXED** |
| Concurrent requests | 10 | **2** | ✅ **FIXED** |
| Embedding model | ~5GB | ~5GB | ✅ **OK** |

## Updated Configuration (User Requested)

### ✅ Re-enabled DeepSeek-R1 70B Model
- **User requested**: Give 70B model room to run
- **Changes made**:
  - Increased `max_model_size_gb`: 24 → 40
  - Reduced `max_concurrent_models`: 2 → 1 (when running 70B model)
  - Re-enabled `deepseek-r1-70b` in model registry
  - Reduced `max_concurrent_requests`: 2 → 1

### ⚠️ Important Notes
1. **70B model (~40GB)**: Will use most of your 32GB VRAM
2. **Concurrent models**: Limited to 1 when 70B is loaded
3. **Performance**: May be slower due to limited VRAM headroom
4. **Monitor**: Watch for OOM errors - may need to unload other models first

## Remaining Considerations

1. **`deepseek-r1-70b` model**: Now enabled, uses ~40GB VRAM (most of your 32GB GPU)
2. **`qwen2.5-32b` model**: ~20GB, still available but can't run with 70B simultaneously
3. **Performance impact**: Smaller batch sizes prevent OOM errors
4. **Concurrent models**: Limited to 1 ensures VRAM is not exceeded when running 70B

## Files Modified

- `backend/llm_orchestrator/multi_llm_client.py` - Disabled 70B model, reduced concurrent requests
- `backend/embedding/embedder.py` - Reduced batch size to 4
- `backend/ingestion/service.py` - Reduced batch size to 4
- `backend/file_manager/adaptive_file_processor.py` - Reduced all batch sizes to 4
