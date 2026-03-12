# Environment Configuration Update Instructions

## Current Settings (Lightweight Mode - No Models)
```bash
SKIP_EMBEDDING_LOAD=true
# EMBEDDING_DEFAULT=qwen_4b
```

## To Enable Lightweight Model (all-MiniLM-L6-v2)

After downloading the model, update your `.env` file with these settings:

```bash
# Embedding Model Configuration
SKIP_EMBEDDING_LOAD=false
EMBEDDING_DEFAULT=all-MiniLM-L6-v2
EMBEDDING_MODEL_PATH=./models/embedding/all-MiniLM-L6-v2
EMBEDDING_DEVICE=cpu
EMBEDDING_NORMALIZE=true
```

## To Switch Back to Qwen-4B (Production)

```bash
# Embedding Model Configuration
SKIP_EMBEDDING_LOAD=false
EMBEDDING_DEFAULT=qwen_4b
EMBEDDING_MODEL_PATH=./models/embedding/qwen_4b
EMBEDDING_DEVICE=cuda  # or cpu if no GPU
EMBEDDING_NORMALIZE=true
```

## Manual Update Steps

1. Open `backend/.env` in your text editor
2. Find the lines starting with `SKIP_EMBEDDING_LOAD` and `EMBEDDING_DEFAULT`
3. Replace them with the settings above
4. Save the file
5. Restart the backend server

**Note:** The `.env` file is gitignored for security, so these changes won't be committed to git.
